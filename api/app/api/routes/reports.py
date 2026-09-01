from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import paginate_query
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.master import Customer, Manufacturer, Product, ProductCategory, Warehouse
from app.models.org import Department, Employee
from app.models.returns import SalesReturn
from app.models.sales import SalesOrder, SalesOrderItem
from app.schemas.common import Page, PageParams, page_of
from app.schemas.reports import (
    CustomerSummaryRow,
    DashboardOut,
    EmployeeSummaryRow,
    OrderDetailRow,
    ProductSummaryRow,
    SalesDailyRow,
    SalesMonthlyRow,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


def _money(value) -> float:
    return round(float(value or 0), 2)


@router.get("/sales-daily", response_model=list[SalesDailyRow], summary="每日销售汇总")
async def sales_daily(
    db: Db,
    _: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = (
        select(
            SalesOrder.order_date,
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.item_count), 0),
            func.coalesce(func.sum(SalesOrder.total_quantity), 0),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.coalesce(func.sum(SalesOrder.discount_amount), 0),
            func.coalesce(func.sum(SalesOrder.cost_amount), 0),
        )
        .where(SalesOrder.status != "已取消")
        .group_by(SalesOrder.order_date)
    )
    if start_date:
        stmt = stmt.where(SalesOrder.order_date >= start_date)
    if end_date:
        stmt = stmt.where(SalesOrder.order_date <= end_date)
    rows = (await db.execute(stmt.order_by(SalesOrder.order_date.desc()))).all()
    return [
        SalesDailyRow(
            sale_date=r[0],
            order_count=r[1],
            item_count=r[2],
            quantity=r[3],
            total_amount=_money(r[4]),
            discount_amount=_money(r[5]),
            cost_amount=_money(r[6]),
            profit_amount=_money(r[4] - r[6]),
        )
        for r in rows
    ]


@router.get("/sales-monthly", response_model=list[SalesMonthlyRow], summary="月度销售汇总（含环比）")
async def sales_monthly(
    db: Db,
    _: CurrentUser,
    start_month: str | None = None,
    end_month: str | None = None,
):
    daily = await sales_daily(db, _)
    monthly: dict[str, dict] = {}
    for row in daily:
        month = row.sale_date.strftime("%Y-%m-01")
        bucket = monthly.setdefault(
            month,
            {
                "month": month,
                "order_count": 0,
                "item_count": 0,
                "quantity": 0,
                "total_amount": 0.0,
                "discount_amount": 0.0,
                "cost_amount": 0.0,
                "profit_amount": 0.0,
            },
        )
        bucket["order_count"] += row.order_count
        bucket["item_count"] += row.item_count
        bucket["quantity"] += row.quantity
        bucket["total_amount"] += row.total_amount
        bucket["discount_amount"] += row.discount_amount
        bucket["cost_amount"] += row.cost_amount
        bucket["profit_amount"] += row.profit_amount

    buckets = sorted(monthly.values(), key=lambda b: b["month"], reverse=True)
    if start_month:
        buckets = [b for b in buckets if b["month"] >= f"{start_month}-01"]
    if end_month:
        buckets = [b for b in buckets if b["month"] <= f"{end_month}-01"]
    result: list[SalesMonthlyRow] = []
    for i, bucket in enumerate(buckets):
        prev = buckets[i + 1]["total_amount"] if i + 1 < len(buckets) else None
        growth = (
            round((bucket["total_amount"] - prev) / prev * 100, 2)
            if prev
            else None
        )
        result.append(
            SalesMonthlyRow(
                month=bucket["month"],
                order_count=bucket["order_count"],
                item_count=bucket["item_count"],
                quantity=bucket["quantity"],
                total_amount=round(bucket["total_amount"], 2),
                discount_amount=round(bucket["discount_amount"], 2),
                cost_amount=round(bucket["cost_amount"], 2),
                profit_amount=round(bucket["profit_amount"], 2),
                prev_month_amount=prev,
                amount_growth_rate=growth,
            )
        )
    return result


@router.get("/customer-summary", response_model=list[CustomerSummaryRow], summary="客户销售汇总")
async def customer_summary(
    db: Db,
    _: CurrentUser,
    keyword: str | None = None,
):
    not_cancelled = SalesOrder.status != "已取消"
    stmt = (
        select(
            Customer.id,
            Customer.code,
            Customer.name,
            Customer.customer_type,
            Customer.coop_level,
            Customer.province,
            Customer.city,
            Customer.phone,
            func.count(SalesOrder.id).filter(not_cancelled),
            func.coalesce(func.sum(SalesOrder.total_amount).filter(not_cancelled), 0),
            func.coalesce(func.sum(SalesOrder.cost_amount).filter(not_cancelled), 0),
            func.max(SalesOrder.order_date).filter(not_cancelled),
        )
        .outerjoin(SalesOrder, SalesOrder.customer_id == Customer.id)
        .group_by(Customer.id)
        .order_by(Customer.id)
    )
    if keyword:
        stmt = stmt.where(
            Customer.name.ilike(f"%{keyword}%") | Customer.code.ilike(f"%{keyword}%")
        )
    rows = (await db.execute(stmt)).all()
    return [
        CustomerSummaryRow(
            customer_id=r[0],
            customer_code=r[1],
            customer_name=r[2],
            customer_type=r[3],
            coop_level=r[4],
            province=r[5],
            city=r[6],
            phone=r[7],
            order_count=r[8],
            total_amount=_money(r[9]),
            cost_amount=_money(r[10]),
            profit_amount=_money(r[9] - r[10]),
            last_order_date=r[11],
        )
        for r in rows
    ]


@router.get("/employee-summary", response_model=list[EmployeeSummaryRow], summary="销售员业绩汇总")
async def employee_summary(
    db: Db,
    _: CurrentUser,
    department_id: int | None = None,
):
    not_cancelled = SalesOrder.status != "已取消"
    stmt = (
        select(
            Employee.id,
            Employee.code,
            Employee.name,
            Department.name,
            Employee.position,
            func.count(SalesOrder.id).filter(not_cancelled),
            func.coalesce(func.sum(SalesOrder.total_amount).filter(not_cancelled), 0),
            func.coalesce(func.sum(SalesOrder.cost_amount).filter(not_cancelled), 0),
            func.count(func.distinct(SalesOrder.customer_id)).filter(not_cancelled),
        )
        .outerjoin(Department, Department.id == Employee.department_id)
        .outerjoin(SalesOrder, SalesOrder.employee_id == Employee.id)
        .group_by(Employee.id, Department.name, Employee.position)
        .order_by(Employee.id)
    )
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    rows = (await db.execute(stmt)).all()
    return [
        EmployeeSummaryRow(
            employee_id=r[0],
            employee_code=r[1],
            employee_name=r[2],
            department_name=r[3],
            position=r[4],
            order_count=r[5],
            total_amount=_money(r[6]),
            cost_amount=_money(r[7]),
            profit_amount=_money(r[6] - r[7]),
            customer_count=r[8],
        )
        for r in rows
    ]


@router.get("/product-summary", response_model=list[ProductSummaryRow], summary="商品销售汇总")
async def product_summary(
    db: Db,
    _: CurrentUser,
    category_id: int | None = None,
):
    stmt = (
        select(
            Product.id,
            Product.sku,
            Product.name,
            ProductCategory.name,
            Manufacturer.name,
            Product.cost_price,
            Product.standard_price,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
            func.coalesce(func.sum(SalesOrderItem.amount), 0),
            func.count(func.distinct(SalesOrder.id)),
        )
        .outerjoin(SalesOrderItem, SalesOrderItem.product_id == Product.id)
        .outerjoin(
            SalesOrder,
            (SalesOrder.id == SalesOrderItem.sales_order_id)
            & (SalesOrder.status != "已取消"),
        )
        .outerjoin(ProductCategory, ProductCategory.id == Product.category_id)
        .outerjoin(Manufacturer, Manufacturer.id == Product.manufacturer_id)
        .group_by(
            Product.id, ProductCategory.name, Manufacturer.name, Product.cost_price, Product.standard_price
        )
        .order_by(Product.id)
    )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    rows = (await db.execute(stmt)).all()
    return [
        ProductSummaryRow(
            product_id=r[0],
            sku=r[1],
            product_name=r[2],
            category_name=r[3],
            manufacturer_name=r[4],
            cost_price=_money(r[5]),
            standard_price=_money(r[6]),
            sold_quantity=r[7],
            sales_amount=_money(r[8]),
            gross_profit=_money(r[8] - (r[7] * r[5])),
            order_count=r[9],
        )
        for r in rows
    ]


@router.get("/order-detail", response_model=Page[OrderDetailRow], summary="订单明细报表")
async def order_detail(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    order_id: int | None = None,
    customer_id: int | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = (
        select(
            SalesOrder.id,
            SalesOrder.order_no,
            SalesOrder.order_date,
            SalesOrder.status,
            Customer.id,
            Customer.name,
            Customer.customer_type,
            Customer.coop_level,
            Employee.id,
            Employee.name,
            Department.name,
            Warehouse.name,
            SalesOrderItem.product_id,
            Product.sku,
            Product.name,
            ProductCategory.name,
            Manufacturer.name,
            SalesOrderItem.quantity,
            SalesOrderItem.unit_price,
            SalesOrderItem.discount_amount,
            SalesOrderItem.amount,
            SalesOrder.total_amount,
            SalesOrder.paid_amount,
        )
        .join(Customer, Customer.id == SalesOrder.customer_id)
        .join(Employee, Employee.id == SalesOrder.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(Warehouse, Warehouse.id == SalesOrder.warehouse_id)
        .join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id)
        .join(Product, Product.id == SalesOrderItem.product_id)
        .join(ProductCategory, ProductCategory.id == Product.category_id)
        .join(Manufacturer, Manufacturer.id == Product.manufacturer_id)
        .order_by(SalesOrder.id.desc(), SalesOrderItem.id)
    )
    if order_id is not None:
        stmt = stmt.where(SalesOrder.id == order_id)
    if customer_id is not None:
        stmt = stmt.where(SalesOrder.customer_id == customer_id)
    if status:
        stmt = stmt.where(SalesOrder.status == status)
    if start_date:
        stmt = stmt.where(SalesOrder.order_date >= start_date)
    if end_date:
        stmt = stmt.where(SalesOrder.order_date <= end_date)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = await db.scalar(count_stmt) or 0
    rows = (await db.execute(stmt.offset((params.page - 1) * params.size).limit(params.size))).all()
    items = [
        OrderDetailRow(
            order_id=r[0],
            order_no=r[1],
            order_date=r[2],
            order_status=r[3],
            customer_id=r[4],
            customer_name=r[5],
            customer_type=r[6],
            coop_level=r[7],
            employee_id=r[8],
            employee_name=r[9],
            department_name=r[10],
            warehouse_name=r[11],
            product_id=r[12],
            sku=r[13],
            product_name=r[14],
            category_name=r[15],
            manufacturer_name=r[16],
            quantity=r[17],
            unit_price=_money(r[18]),
            discount_amount=_money(r[19]),
            line_amount=_money(r[20]),
            order_amount=_money(r[21]),
            paid_amount=_money(r[22]),
        )
        for r in rows
    ]
    return page_of(items, total, params.page, params.size)


@router.get("/inventory-status", response_model=list[dict], summary="库存状态报表")
async def inventory_status(db: Db, _: CurrentUser, warehouse_id: int | None = None):
    from app.api.routes.inventory import list_inventory
    from app.schemas.common import PageParams

    result = await list_inventory(
        db, PageParams(page=1, size=200), _, warehouse_id=warehouse_id
    )
    return [item.model_dump() for item in result.items]


@router.get("/dashboard", response_model=DashboardOut, summary="综合经营看板")
async def dashboard(db: Db, _: CurrentUser):
    today = date.today()
    month_start = today.replace(day=1)

    today_stmt = select(
        func.count(SalesOrder.id),
        func.coalesce(func.sum(SalesOrder.total_amount), 0),
        func.coalesce(func.sum(SalesOrder.total_amount - SalesOrder.cost_amount), 0),
    ).where(SalesOrder.order_date == today, SalesOrder.status != "已取消")
    t = (await db.execute(today_stmt)).one()

    month_stmt = select(
        func.count(SalesOrder.id),
        func.coalesce(func.sum(SalesOrder.total_amount), 0),
        func.coalesce(func.sum(SalesOrder.total_amount - SalesOrder.cost_amount), 0),
    ).where(SalesOrder.order_date >= month_start, SalesOrder.status != "已取消")
    m = (await db.execute(month_stmt)).one()

    low_stock = await db.scalar(
        select(func.count(Inventory.id)).where(Inventory.quantity < Inventory.safety_stock)
    )
    pending_returns = await db.scalar(
        select(func.count(SalesReturn.id)).where(SalesReturn.status == "待处理")
    )

    receivable_rows = (
        await db.execute(
            select(SalesOrder.total_amount, SalesOrder.paid_amount).where(
                SalesOrder.status != "已取消"
            )
        )
    ).all()
    total_receivable = sum(
        float(r[0]) - float(r[1]) for r in receivable_rows if float(r[0]) - float(r[1]) > 0
    )

    return DashboardOut(
        today_order_count=t[0],
        today_sales_amount=_money(t[1]),
        today_profit=_money(t[2]),
        month_order_count=m[0],
        month_sales_amount=_money(m[1]),
        month_profit=_money(m[2]),
        low_stock_count=low_stock or 0,
        pending_return_count=pending_returns or 0,
        total_receivable=_money(total_receivable),
    )
