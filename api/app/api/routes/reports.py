from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import like_contains
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.master import Customer, Manufacturer, Product, ProductCategory, Warehouse
from app.models.org import Department, Employee
from app.models.rollup import (
    SalesRollupCustomer,
    SalesRollupDay,
    SalesRollupEmployee,
    SalesRollupEmployeeCustomer,
    SalesRollupProduct,
)
from app.models.returns import SalesReturn
from app.models.sales import SalesOrder, SalesOrderItem
from app.schemas.common import Page, PageParams, page_of
from app.schemas.inventory import InventoryOut
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
PERM_REPORT = Depends(require_permission("report:view"))
PERM_DASHBOARD = Depends(require_permission("dashboard:view"))


def _money(value) -> float:
    return round(float(value or 0), 2)


async def _sales_daily_rows(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[SalesDailyRow]:
    """按日读取销售汇总（内部复用，不做分页）。

    数据来自 ``sales_rollup_day``（已按日预聚合），不再是每次请求扫描全量订单表。
    """
    stmt = select(
        SalesRollupDay.order_date,
        SalesRollupDay.order_count,
        SalesRollupDay.item_count,
        SalesRollupDay.quantity,
        SalesRollupDay.total_amount,
        SalesRollupDay.discount_amount,
        SalesRollupDay.cost_amount,
    )
    if start_date:
        stmt = stmt.where(SalesRollupDay.order_date >= start_date)
    if end_date:
        stmt = stmt.where(SalesRollupDay.order_date <= end_date)
    rows = (await db.execute(stmt.order_by(SalesRollupDay.order_date.desc()))).all()
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


@router.get("/sales-daily", response_model=Page[SalesDailyRow], summary="每日销售汇总", dependencies=[PERM_REPORT])
async def sales_daily(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
):
    # 汇总表里最多只有「天数」量级的行（当前 1600 多行），全量取出后内存分页即可，
    # 不需要为分页再跑一遍聚合算 total。
    items = await _sales_daily_rows(db, start_date=start_date, end_date=end_date)
    total = len(items)
    start = (params.page - 1) * params.size
    return page_of(items[start : start + params.size], total, params.page, params.size)


@router.get(
    "/sales-monthly",
    response_model=Page[SalesMonthlyRow],
    summary="月度销售汇总（含环比）",
    dependencies=[PERM_REPORT],
)
async def sales_monthly(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    start_month: str | None = None,
    end_month: str | None = None,
):
    daily = await _sales_daily_rows(db)
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
    total = len(result)
    start = (params.page - 1) * params.size
    return page_of(result[start : start + params.size], total, params.page, params.size)


@router.get("/customer-summary", response_model=Page[CustomerSummaryRow], summary="客户销售汇总", dependencies=[PERM_REPORT])
async def customer_summary(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
    customer_id: int | None = None,
):
    # 读「按客户」汇总表（客户量级 1500 多行），不再对全量订单做 join + 分组
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
            func.coalesce(SalesRollupCustomer.order_count, 0),
            func.coalesce(SalesRollupCustomer.total_amount, 0),
            func.coalesce(SalesRollupCustomer.cost_amount, 0),
            SalesRollupCustomer.last_order_date,
        )
        .outerjoin(SalesRollupCustomer, SalesRollupCustomer.customer_id == Customer.id)
        .order_by(
            func.coalesce(SalesRollupCustomer.total_amount, 0).desc(),
            Customer.id,
        )
    )
    if keyword:
        stmt = stmt.where(
            Customer.name.ilike(f"%{keyword}%") | Customer.code.ilike(f"%{keyword}%")
        )
    if customer_id is not None:
        stmt = stmt.where(Customer.id == customer_id)
    rows = (await db.execute(stmt)).all()
    items = [
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
    total = len(items)
    start = (params.page - 1) * params.size
    return page_of(items[start : start + params.size], total, params.page, params.size)


@router.get("/employee-summary", response_model=Page[EmployeeSummaryRow], summary="销售员业绩汇总", dependencies=[PERM_REPORT])
async def employee_summary(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    employee_id: int | None = None,
    department_id: int | None = None,
):
    # 金额 / 单数来自「按销售员」汇总表；成交客户数是去重计数，
    # 由 sales_rollup_employee_customer 这张对表按销售员数行数得出。
    customer_counts = (
        select(
            SalesRollupEmployeeCustomer.employee_id.label("employee_id"),
            func.count().label("customer_count"),
        )
        .group_by(SalesRollupEmployeeCustomer.employee_id)
        .subquery()
    )
    stmt = (
        select(
            Employee.id,
            Employee.code,
            Employee.name,
            Department.name,
            Employee.position,
            func.coalesce(SalesRollupEmployee.order_count, 0),
            func.coalesce(SalesRollupEmployee.total_amount, 0),
            func.coalesce(SalesRollupEmployee.cost_amount, 0),
            func.coalesce(customer_counts.c.customer_count, 0),
        )
        .outerjoin(Department, Department.id == Employee.department_id)
        .outerjoin(SalesRollupEmployee, SalesRollupEmployee.employee_id == Employee.id)
        .outerjoin(customer_counts, customer_counts.c.employee_id == Employee.id)
        .order_by(
            func.coalesce(SalesRollupEmployee.total_amount, 0).desc(),
            Employee.id,
        )
    )
    if employee_id is not None:
        stmt = stmt.where(Employee.id == employee_id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    rows = (await db.execute(stmt)).all()
    items = [
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
    total = len(items)
    start = (params.page - 1) * params.size
    return page_of(items[start : start + params.size], total, params.page, params.size)


@router.get("/product-summary", response_model=Page[ProductSummaryRow], summary="商品销售汇总", dependencies=[PERM_REPORT])
async def product_summary(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    product_id: int | None = None,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
):
    """读「按商品」汇总表（当前 300 多行）。

    注意：汇总表里只有数量 / 金额 / 订单数，**毛利的口径依赖商品当前成本价**
    （``product.cost_price``），所以毛利率在查询时按同一公式现算，保持与
    重建前的数值完全一致。
    """
    stmt = (
        select(
            Product.id,
            Product.sku,
            Product.name,
            ProductCategory.name,
            Manufacturer.name,
            Product.cost_price,
            Product.standard_price,
            func.coalesce(SalesRollupProduct.quantity, 0),
            func.coalesce(SalesRollupProduct.sales_amount, 0),
            func.coalesce(SalesRollupProduct.order_count, 0),
        )
        .outerjoin(SalesRollupProduct, SalesRollupProduct.product_id == Product.id)
        .outerjoin(ProductCategory, ProductCategory.id == Product.category_id)
        .outerjoin(Manufacturer, Manufacturer.id == Product.manufacturer_id)
        .order_by(
            func.coalesce(SalesRollupProduct.sales_amount, 0).desc(),
            Product.id,
        )
    )
    if product_id is not None:
        stmt = stmt.where(Product.id == product_id)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if manufacturer_id is not None:
        stmt = stmt.where(Product.manufacturer_id == manufacturer_id)

    rows = (await db.execute(stmt)).all()
    items = [
        ProductSummaryRow(
            product_id=r[0],
            sku=r[1],
            product_name=r[2],
            category_name=r[3],
            manufacturer_name=r[4],
            cost_price=_money(r[5]),
            standard_price=_money(r[6]),
            sold_quantity=int(r[7]),
            sales_amount=_money(r[8]),
            gross_profit=_money(float(r[8]) - (int(r[7]) * float(r[5]))),
            order_count=int(r[9]),
        )
        for r in rows
    ]
    total = len(items)
    start = (params.page - 1) * params.size
    return page_of(items[start : start + params.size], total, params.page, params.size)


@router.get("/order-detail", response_model=Page[OrderDetailRow], summary="订单明细报表", dependencies=[PERM_REPORT])
async def order_detail(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    order_id: int | None = None,
    order_no: str | None = None,
    customer_id: int | None = None,
    product_id: int | None = None,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
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
    if order_no and order_no.strip():
        # 单号查询是最常用的入口：支持输入片段（粘贴完整单号或只打前几位都能命中）。
        stmt = stmt.where(like_contains(SalesOrder.order_no, order_no))
    if customer_id is not None:
        stmt = stmt.where(SalesOrder.customer_id == customer_id)
    if product_id is not None:
        stmt = stmt.where(SalesOrderItem.product_id == product_id)
    if category_id is not None:
        stmt = stmt.where(ProductCategory.id == category_id)
    if manufacturer_id is not None:
        stmt = stmt.where(Manufacturer.id == manufacturer_id)
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


@router.get("/inventory-status", response_model=Page[InventoryOut], summary="库存状态报表", dependencies=[PERM_REPORT])
async def inventory_status(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    warehouse_id: int | None = None,
    product_id: int | None = None,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
):
    from app.api.routes.inventory import list_inventory

    return await list_inventory(
        db,
        params,
        _,
        warehouse_id=warehouse_id,
        product_id=product_id,
        category_id=category_id,
        manufacturer_id=manufacturer_id,
    )


@router.get("/dashboard", response_model=DashboardOut, summary="综合经营看板", dependencies=[PERM_DASHBOARD])
async def dashboard(db: Db, _: CurrentUser):
    today = date.today()
    month_start = today.replace(day=1)

    # 当日 / 当月口径读按日汇总表（命中 1~31 行），不再每次请求扫全量订单表
    def _period_stmt(condition):
        return select(
            func.coalesce(func.sum(SalesRollupDay.order_count), 0),
            func.coalesce(func.sum(SalesRollupDay.total_amount), 0),
            func.coalesce(
                func.sum(SalesRollupDay.total_amount - SalesRollupDay.cost_amount), 0
            ),
        ).where(condition)

    t = (await db.execute(_period_stmt(SalesRollupDay.order_date == today))).one()
    m = (
        await db.execute(_period_stmt(SalesRollupDay.order_date >= month_start))
    ).one()

    low_stock = await db.scalar(
        select(func.count(Inventory.id)).where(Inventory.quantity < Inventory.safety_stock)
    )
    pending_returns = await db.scalar(
        select(func.count(SalesReturn.id)).where(SalesReturn.status == "待处理")
    )

    # 应收余额 = Σ max(订单金额 - 已收金额, 0)：先对每张订单取 max 再求和，
    # 无法用可累加的汇总列表达（收款会改动历史订单，不属于"按订单日期"的维度），
    # 因此下推成 SQL 单条聚合，避免把 20 万行订单拉进 Python 再求和。
    outstanding = SalesOrder.total_amount - SalesOrder.paid_amount
    total_receivable = await db.scalar(
        select(
            func.coalesce(func.sum(case((outstanding > 0, outstanding), else_=0)), 0)
        ).where(SalesOrder.status != "已取消")
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
