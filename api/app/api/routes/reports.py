import time
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import like_contains, paginate_query
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.master import Customer, Manufacturer, Product, ProductCategory, Warehouse
from app.models.org import Department, Employee
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


# 商品销售汇总需要聚合百万级销售明细，结果按商品仅 365 行；
# 缓存后翻页/切换每页条数可即时返回，避免每次请求重算。
# 缓存键是筛选条件组合（商品 / 分类 / 厂家），键空间很小。
_PRODUCT_SUMMARY_TTL_SECONDS = 60.0
ProductSummaryKey = tuple[int | None, int | None, int | None]
_product_summary_cache: dict[ProductSummaryKey, tuple[float, list]] = {}


def invalidate_product_summary_cache() -> None:
    """销售订单发生新增/取消/删除后调用，确保汇总及时刷新。"""
    _product_summary_cache.clear()


def _product_summary_cached(key: ProductSummaryKey):
    entry = _product_summary_cache.get(key)
    if entry and entry[0] > time.monotonic():
        return entry[1]
    return None


def _product_summary_store(key: ProductSummaryKey, value: list) -> None:
    _product_summary_cache[key] = (time.monotonic() + _PRODUCT_SUMMARY_TTL_SECONDS, value)


async def _sales_daily_rows(
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[SalesDailyRow]:
    """按日聚合销售数据（内部复用，不做分页）。"""
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


@router.get("/sales-daily", response_model=Page[SalesDailyRow], summary="每日销售汇总", dependencies=[PERM_REPORT])
async def sales_daily(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
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
    stmt = stmt.order_by(SalesOrder.order_date.desc())
    total = (
        await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ) or 0
    rows = (
        await db.execute(stmt.offset((params.page - 1) * params.size).limit(params.size))
    ).all()
    items = [
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
    return page_of(items, total, params.page, params.size)


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
        .order_by(
            func.coalesce(func.sum(SalesOrder.total_amount).filter(not_cancelled), 0).desc(),
            Customer.id,
        )
    )
    if keyword:
        stmt = stmt.where(
            Customer.name.ilike(f"%{keyword}%") | Customer.code.ilike(f"%{keyword}%")
        )
    if customer_id is not None:
        stmt = stmt.where(Customer.id == customer_id)
    total = (
        await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ) or 0
    rows = (
        await db.execute(stmt.offset((params.page - 1) * params.size).limit(params.size))
    ).all()
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
    return page_of(items, total, params.page, params.size)


@router.get("/employee-summary", response_model=Page[EmployeeSummaryRow], summary="销售员业绩汇总", dependencies=[PERM_REPORT])
async def employee_summary(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    employee_id: int | None = None,
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
        .order_by(
            func.coalesce(func.sum(SalesOrder.total_amount).filter(not_cancelled), 0).desc(),
            Employee.id,
        )
    )
    if employee_id is not None:
        stmt = stmt.where(Employee.id == employee_id)
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    total = (
        await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ) or 0
    rows = (
        await db.execute(stmt.offset((params.page - 1) * params.size).limit(params.size))
    ).all()
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
    return page_of(items, total, params.page, params.size)


async def _compute_product_summary(
    db: AsyncSession,
    *,
    product_id: int | None = None,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
) -> list[ProductSummaryRow]:
    """按商品聚合销售明细（供商品销售汇总报表）。

    性能要点（对约 160 万行销售明细，实测 4.7s → 0.8s）：
    - 用 `NOT IN (已取消订单)` 反向过滤，避免与 20 万订单做大表连接；
    - 把「去重订单数」拆成独立子查询，避免 `count(distinct)` 触发对 160 万行的磁盘排序。
    """
    cancelled_orders = select(SalesOrder.id).where(SalesOrder.status == "已取消")

    sum_agg = (
        select(
            SalesOrderItem.product_id.label("pid"),
            func.sum(SalesOrderItem.quantity).label("sold_qty"),
            func.sum(SalesOrderItem.amount).label("sales_amt"),
        )
        .where(SalesOrderItem.sales_order_id.not_in(cancelled_orders))
        .group_by(SalesOrderItem.product_id)
        .subquery()
    )

    # 商品-订单去重后在数据库层按商品计数（利用 idx_sales_order_item_product 索引顺序去重）
    order_pairs = (
        select(
            SalesOrderItem.product_id.label("pid"),
            SalesOrderItem.sales_order_id.label("oid"),
        )
        .distinct()
        .subquery()
    )
    order_agg = (
        select(order_pairs.c.pid, func.count().label("order_cnt"))
        .where(order_pairs.c.oid.not_in(cancelled_orders))
        .group_by(order_pairs.c.pid)
        .subquery()
    )

    stmt = (
        select(
            Product.id,
            Product.sku,
            Product.name,
            ProductCategory.name,
            Manufacturer.name,
            Product.cost_price,
            Product.standard_price,
            func.coalesce(sum_agg.c.sold_qty, 0),
            func.coalesce(sum_agg.c.sales_amt, 0),
            func.coalesce(order_agg.c.order_cnt, 0),
        )
        .outerjoin(sum_agg, sum_agg.c.pid == Product.id)
        .outerjoin(order_agg, order_agg.c.pid == Product.id)
        .outerjoin(ProductCategory, ProductCategory.id == Product.category_id)
        .outerjoin(Manufacturer, Manufacturer.id == Product.manufacturer_id)
        .order_by(func.coalesce(sum_agg.c.sales_amt, 0).desc(), Product.id)
    )
    if product_id is not None:
        stmt = stmt.where(Product.id == product_id)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if manufacturer_id is not None:
        stmt = stmt.where(Product.manufacturer_id == manufacturer_id)

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
            sold_quantity=int(r[7]),
            sales_amount=_money(r[8]),
            gross_profit=_money(float(r[8]) - (int(r[7]) * float(r[5]))),
            order_count=int(r[9]),
        )
        for r in rows
    ]


@router.get("/product-summary", response_model=Page[ProductSummaryRow], summary="商品销售汇总", dependencies=[PERM_REPORT])
async def product_summary(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    product_id: int | None = None,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
):
    key: ProductSummaryKey = (product_id, category_id, manufacturer_id)
    items = _product_summary_cached(key)
    if items is None:
        items = await _compute_product_summary(
            db,
            product_id=product_id,
            category_id=category_id,
            manufacturer_id=manufacturer_id,
        )
        _product_summary_store(key, items)
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
