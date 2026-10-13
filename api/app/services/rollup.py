"""销售报表汇总表的维护（按键重算）。

调用约定
--------
写路径负责三件事，顺序不能变：

1. 改动订单**之前**调用 ``capture_order_keys(db, order)`` 记下受影响的键；
2. 完成业务写入（新增 / 取消 / 删除）；
3. 调用 ``refresh_rollups(db, keys)``，然后 ``commit``。

第 1 步必须在改动之前，因为取消 / 删除后订单的原值就取不到了；这也正是本模块
按"键"而不是按"旧值减新值"维护的原因——重算只需要知道**哪些键**脏了。

``refresh_rollups`` 先 ``flush``，因此调用方不必自己保证待写数据已落库。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.rollup import (
    SalesRollupCustomer,
    SalesRollupDay,
    SalesRollupEmployee,
    SalesRollupEmployeeCustomer,
    SalesRollupProduct,
)
from app.models.sales import SalesOrder, SalesOrderItem

# 与报表口径一致：已取消订单不计入任何销售汇总
NOT_CANCELLED = SalesOrder.status != "已取消"

# 金额比对容差（分）：Decimal 求和与存储精度在两种数据库上可能有末位差异
_MONEY_TOLERANCE = 0.01


@dataclass
class RollupKeys:
    """一次业务改动影响到的汇总主键集合。"""

    dates: set[date] = field(default_factory=set)
    product_ids: set[int] = field(default_factory=set)
    customer_ids: set[int] = field(default_factory=set)
    employee_ids: set[int] = field(default_factory=set)

    def merge(self, other: "RollupKeys") -> None:
        self.dates |= other.dates
        self.product_ids |= other.product_ids
        self.customer_ids |= other.customer_ids
        self.employee_ids |= other.employee_ids

    @property
    def is_empty(self) -> bool:
        return not (
            self.dates or self.product_ids or self.customer_ids or self.employee_ids
        )


async def capture_order_keys(db: AsyncSession, order: SalesOrder) -> RollupKeys:
    """记录一张订单在汇总表里占用的键（必须在改动订单之前调用）。"""
    product_ids = set(
        await db.scalars(
            select(SalesOrderItem.product_id).where(
                SalesOrderItem.sales_order_id == order.id
            )
        )
    )
    return RollupKeys(
        dates={order.order_date},
        product_ids=product_ids,
        customer_ids={order.customer_id},
        employee_ids={order.employee_id},
    )


async def keys_for_dates(db: AsyncSession, dates: Iterable[date]) -> RollupKeys:
    """某个（些）业务日期下所有订单占用的键，供按天重算 / 修复使用。"""
    date_set = set(dates)
    keys = RollupKeys(dates=date_set)
    if not date_set:
        return keys
    keys.customer_ids = set(
        await db.scalars(select(SalesOrder.customer_id).where(SalesOrder.order_date.in_(date_set)))
    )
    keys.employee_ids = set(
        await db.scalars(select(SalesOrder.employee_id).where(SalesOrder.order_date.in_(date_set)))
    )
    keys.product_ids = set(
        await db.scalars(
            select(SalesOrderItem.product_id)
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
            .where(SalesOrder.order_date.in_(date_set))
        )
    )
    return keys


# ---------------------------------------------------------------------------
# 各粒度的聚合语句：keys 为 None 表示"全量"
# ---------------------------------------------------------------------------


def _day_select(dates: set[date] | None) -> Select:
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
        .where(NOT_CANCELLED)
        .group_by(SalesOrder.order_date)
    )
    if dates is not None:
        stmt = stmt.where(SalesOrder.order_date.in_(dates))
    return stmt


def _product_select(product_ids: set[int] | None) -> Select:
    stmt = (
        select(
            SalesOrderItem.product_id,
            func.coalesce(func.sum(SalesOrderItem.quantity), 0),
            func.coalesce(func.sum(SalesOrderItem.amount), 0),
            func.count(func.distinct(SalesOrderItem.sales_order_id)),
        )
        .select_from(SalesOrderItem)
        .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
        .where(NOT_CANCELLED)
        .group_by(SalesOrderItem.product_id)
    )
    if product_ids is not None:
        stmt = stmt.where(SalesOrderItem.product_id.in_(product_ids))
    return stmt


def _customer_select(customer_ids: set[int] | None) -> Select:
    stmt = (
        select(
            SalesOrder.customer_id,
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.coalesce(func.sum(SalesOrder.cost_amount), 0),
            func.max(SalesOrder.order_date),
        )
        .where(NOT_CANCELLED)
        .group_by(SalesOrder.customer_id)
    )
    if customer_ids is not None:
        stmt = stmt.where(SalesOrder.customer_id.in_(customer_ids))
    return stmt


def _employee_select(employee_ids: set[int] | None) -> Select:
    stmt = (
        select(
            SalesOrder.employee_id,
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.coalesce(func.sum(SalesOrder.cost_amount), 0),
        )
        .where(NOT_CANCELLED)
        .group_by(SalesOrder.employee_id)
    )
    if employee_ids is not None:
        stmt = stmt.where(SalesOrder.employee_id.in_(employee_ids))
    return stmt


def _employee_customer_select(employee_ids: set[int] | None) -> Select:
    stmt = (
        select(SalesOrder.employee_id, SalesOrder.customer_id)
        .where(NOT_CANCELLED)
        .group_by(SalesOrder.employee_id, SalesOrder.customer_id)
    )
    if employee_ids is not None:
        stmt = stmt.where(SalesOrder.employee_id.in_(employee_ids))
    return stmt


# ---------------------------------------------------------------------------
# 重算
# ---------------------------------------------------------------------------


def _rows_to_dicts(rows: Iterable, fields: tuple[str, ...]) -> list[dict]:
    return [dict(zip(fields, row, strict=True)) for row in rows]


async def _refresh_day(db: AsyncSession, dates: set[date] | None) -> None:
    stmt_del = delete(SalesRollupDay)
    if dates is not None:
        stmt_del = stmt_del.where(SalesRollupDay.order_date.in_(dates))
    await db.execute(stmt_del)
    rows = (await db.execute(_day_select(dates))).all()
    if rows:
        await db.execute(
            insert(SalesRollupDay),
            _rows_to_dicts(
                rows,
                (
                    "order_date",
                    "order_count",
                    "item_count",
                    "quantity",
                    "total_amount",
                    "discount_amount",
                    "cost_amount",
                ),
            ),
        )


async def _refresh_product(db: AsyncSession, product_ids: set[int] | None) -> None:
    stmt_del = delete(SalesRollupProduct)
    if product_ids is not None:
        stmt_del = stmt_del.where(SalesRollupProduct.product_id.in_(product_ids))
    await db.execute(stmt_del)
    rows = (await db.execute(_product_select(product_ids))).all()
    if rows:
        await db.execute(
            insert(SalesRollupProduct),
            _rows_to_dicts(rows, ("product_id", "quantity", "sales_amount", "order_count")),
        )


async def _refresh_customer(db: AsyncSession, customer_ids: set[int] | None) -> None:
    stmt_del = delete(SalesRollupCustomer)
    if customer_ids is not None:
        stmt_del = stmt_del.where(SalesRollupCustomer.customer_id.in_(customer_ids))
    await db.execute(stmt_del)
    rows = (await db.execute(_customer_select(customer_ids))).all()
    if rows:
        await db.execute(
            insert(SalesRollupCustomer),
            _rows_to_dicts(
                rows,
                (
                    "customer_id",
                    "order_count",
                    "total_amount",
                    "cost_amount",
                    "last_order_date",
                ),
            ),
        )


async def _refresh_employee(db: AsyncSession, employee_ids: set[int] | None) -> None:
    stmt_del = delete(SalesRollupEmployee)
    if employee_ids is not None:
        stmt_del = stmt_del.where(SalesRollupEmployee.employee_id.in_(employee_ids))
    await db.execute(stmt_del)
    rows = (await db.execute(_employee_select(employee_ids))).all()
    if rows:
        await db.execute(
            insert(SalesRollupEmployee),
            _rows_to_dicts(
                rows, ("employee_id", "order_count", "total_amount", "cost_amount")
            ),
        )


async def _refresh_employee_customer(
    db: AsyncSession, employee_ids: set[int] | None
) -> None:
    stmt_del = delete(SalesRollupEmployeeCustomer)
    if employee_ids is not None:
        stmt_del = stmt_del.where(
            SalesRollupEmployeeCustomer.employee_id.in_(employee_ids)
        )
    await db.execute(stmt_del)
    rows = (await db.execute(_employee_customer_select(employee_ids))).all()
    if rows:
        await db.execute(
            insert(SalesRollupEmployeeCustomer),
            _rows_to_dicts(rows, ("employee_id", "customer_id")),
        )


async def refresh_rollups(db: AsyncSession, keys: RollupKeys) -> None:
    """按键重算受影响的汇总行（幂等；调用方负责 commit）。"""
    if keys.is_empty:
        return
    # 让调用方的待写数据（新增明细、状态变更）对下面的聚合可见
    await db.flush()
    if keys.dates:
        await _refresh_day(db, keys.dates)
    if keys.product_ids:
        await _refresh_product(db, keys.product_ids)
    if keys.customer_ids:
        await _refresh_customer(db, keys.customer_ids)
    if keys.employee_ids:
        await _refresh_employee(db, keys.employee_ids)
        await _refresh_employee_customer(db, keys.employee_ids)


async def rebuild_all(db: AsyncSession) -> None:
    """全量重建所有汇总表（首次上线回填、夜间对账、修复漏掉的写路径）。"""
    await _refresh_day(db, None)
    await _refresh_product(db, None)
    await _refresh_customer(db, None)
    await _refresh_employee(db, None)
    await _refresh_employee_customer(db, None)


async def has_rollup_data(db: AsyncSession) -> bool:
    """汇总表是否已回填（供启动自检提示用）。"""
    count = await db.scalar(select(func.count()).select_from(SalesRollupDay))
    return bool(count)


# ---------------------------------------------------------------------------
# 对账
# ---------------------------------------------------------------------------


def _same_money(left, right) -> bool:
    return abs(float(left or 0) - float(right or 0)) <= _MONEY_TOLERANCE


async def check_consistency(db: AsyncSession) -> list[str]:
    """汇总表与明细表的对账结果，返回不一致项（空列表表示一致）。

    比对的是总量口径（金额合计、行数、去重键数量）——增量维护一旦漏掉某条写
    路径，这些指标几乎必然会偏，而成本远低于逐键比对。
    """
    issues: list[str] = []

    raw_day = (
        await db.execute(
            select(
                func.count(SalesOrder.id),
                func.coalesce(func.sum(SalesOrder.total_amount), 0),
                func.coalesce(func.sum(SalesOrder.total_quantity), 0),
                func.count(func.distinct(SalesOrder.order_date)),
            ).where(NOT_CANCELLED)
        )
    ).one()
    roll_day = (
        await db.execute(
            select(
                func.coalesce(func.sum(SalesRollupDay.order_count), 0),
                func.coalesce(func.sum(SalesRollupDay.total_amount), 0),
                func.coalesce(func.sum(SalesRollupDay.quantity), 0),
                func.count(),
            ).select_from(SalesRollupDay)
        )
    ).one()
    if raw_day[0] != roll_day[0]:
        issues.append(f"sales_rollup_day 订单数：明细 {raw_day[0]} ≠ 汇总 {roll_day[0]}")
    if not _same_money(raw_day[1], roll_day[1]):
        issues.append(
            f"sales_rollup_day 销售金额：明细 {raw_day[1]} ≠ 汇总 {roll_day[1]}"
        )
    if raw_day[2] != roll_day[2]:
        issues.append(f"sales_rollup_day 销售数量：明细 {raw_day[2]} ≠ 汇总 {roll_day[2]}")
    if raw_day[3] != roll_day[3]:
        issues.append(f"sales_rollup_day 日期数：明细 {raw_day[3]} ≠ 汇总 {roll_day[3]}")

    raw_product = (
        await db.execute(
            select(
                func.coalesce(func.sum(SalesOrderItem.quantity), 0),
                func.coalesce(func.sum(SalesOrderItem.amount), 0),
                func.count(func.distinct(SalesOrderItem.product_id)),
            )
            .select_from(SalesOrderItem)
            .join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id)
            .where(NOT_CANCELLED)
        )
    ).one()
    roll_product = (
        await db.execute(
            select(
                func.coalesce(func.sum(SalesRollupProduct.quantity), 0),
                func.coalesce(func.sum(SalesRollupProduct.sales_amount), 0),
                func.count(),
            ).select_from(SalesRollupProduct)
        )
    ).one()
    if raw_product[0] != roll_product[0]:
        issues.append(
            f"sales_rollup_product 销售数量：明细 {raw_product[0]} ≠ 汇总 {roll_product[0]}"
        )
    if not _same_money(raw_product[1], roll_product[1]):
        issues.append(
            f"sales_rollup_product 销售金额：明细 {raw_product[1]} ≠ 汇总 {roll_product[1]}"
        )
    if raw_product[2] != roll_product[2]:
        issues.append(
            f"sales_rollup_product 商品数：明细 {raw_product[2]} ≠ 汇总 {roll_product[2]}"
        )

    for model, column, label in (
        (SalesRollupCustomer, SalesOrder.customer_id, "客户"),
        (SalesRollupEmployee, SalesOrder.employee_id, "销售员"),
    ):
        raw = (
            await db.execute(
                select(
                    func.count(SalesOrder.id),
                    func.coalesce(func.sum(SalesOrder.total_amount), 0),
                    func.count(func.distinct(column)),
                ).where(NOT_CANCELLED)
            )
        ).one()
        roll = (
            await db.execute(
                select(
                    func.coalesce(func.sum(model.order_count), 0),
                    func.coalesce(func.sum(model.total_amount), 0),
                    func.count(),
                ).select_from(model)
            )
        ).one()
        if raw[0] != roll[0]:
            issues.append(f"{model.__tablename__} 订单数：明细 {raw[0]} ≠ 汇总 {roll[0]}")
        if not _same_money(raw[1], roll[1]):
            issues.append(f"{model.__tablename__} 销售金额：明细 {raw[1]} ≠ 汇总 {roll[1]}")
        if raw[2] != roll[2]:
            issues.append(f"{model.__tablename__} {label}数：明细 {raw[2]} ≠ 汇总 {roll[2]}")

    raw_pairs = (
        await db.execute(
            select(func.count())
            .select_from(
                select(SalesOrder.employee_id, SalesOrder.customer_id)
                .where(NOT_CANCELLED)
                .group_by(SalesOrder.employee_id, SalesOrder.customer_id)
                .subquery()
            )
        )
    ).scalar() or 0
    roll_pairs = (
        await db.execute(
            select(func.count()).select_from(SalesRollupEmployeeCustomer)
        )
    ).scalar() or 0
    if raw_pairs != roll_pairs:
        issues.append(
            f"sales_rollup_employee_customer 客户数：明细 {raw_pairs} ≠ 汇总 {roll_pairs}"
        )

    return issues
