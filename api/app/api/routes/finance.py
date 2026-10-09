from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, paginate_query
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.models.finance import PaymentRecord
from app.models.master import Customer
from app.models.sales import SalesOrder
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.finance import PaymentCreate, PaymentOut, ReceivableRow

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
PERM_VIEW = Depends(require_permission("finance:view"))
PERM_MANAGE = Depends(require_permission("finance:manage"))


@router.get("/payments", response_model=Page[PaymentOut], summary="收款记录列表", dependencies=[PERM_VIEW])
async def list_payments(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    customer_id: int | None = None,
    sales_order_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = select(PaymentRecord).order_by(PaymentRecord.id.desc())
    if customer_id is not None:
        stmt = stmt.where(PaymentRecord.customer_id == customer_id)
    if sales_order_id is not None:
        stmt = stmt.where(PaymentRecord.sales_order_id == sales_order_id)
    if start_date:
        stmt = stmt.where(PaymentRecord.payment_date >= start_date)
    if end_date:
        stmt = stmt.where(PaymentRecord.payment_date <= end_date)
    rows, total = await paginate_query(db, stmt, params.page, params.size)
    return page_of(rows, total, params.page, params.size)


@router.get("/payments/{payment_id}", response_model=PaymentOut, summary="收款记录详情", dependencies=[PERM_VIEW])
async def get_payment(payment_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, PaymentRecord, payment_id, "收款记录不存在")


@router.post("/payments", response_model=PaymentOut, status_code=201, summary="登记收款", dependencies=[PERM_MANAGE])
async def create_payment(payload: PaymentCreate, db: Db, _: CurrentUser):
    order = await db.get(SalesOrder, payload.sales_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status == "已取消":
        raise HTTPException(status_code=400, detail="已取消订单不能收款")
    remaining = float(order.total_amount) - float(order.paid_amount)
    if payload.amount > remaining + 1e-6:
        raise HTTPException(
            status_code=400,
            detail=f"收款金额超过订单剩余应收（剩余 {remaining:.2f}）",
        )
    payment = PaymentRecord(
        sales_order_id=order.id,
        customer_id=order.customer_id,
        payment_date=payload.payment_date,
        amount=payload.amount,
        payment_method=payload.payment_method,
        status=payload.status,
        remark=payload.remark or order.order_no,
    )
    payment = await create_and_commit(db, payment)
    order.paid_amount = float(order.paid_amount) + payload.amount
    if float(order.paid_amount) >= float(order.total_amount) - 1e-6:
        order.status = "已完成"
    await db.commit()
    await db.refresh(payment)
    return payment


@router.delete("/payments/{payment_id}", response_model=Message, summary="删除收款记录", dependencies=[PERM_MANAGE])
async def delete_payment(payment_id: int, db: Db, _: CurrentUser):
    payment = await get_or_404(db, PaymentRecord, payment_id, "收款记录不存在")
    await delete_and_commit(db, payment)
    return Message(message="收款记录已删除")


@router.get("/receivables", response_model=Page[ReceivableRow], summary="应收账龄分析", dependencies=[PERM_VIEW])
async def list_receivables(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    as_of: date | None = None,
    customer_id: int | None = None,
):
    today = as_of or date.today()
    conditions = [
        SalesOrder.status != "已取消",
        (SalesOrder.total_amount - SalesOrder.paid_amount) > 1e-6,
    ]
    if customer_id is not None:
        conditions.append(SalesOrder.customer_id == customer_id)

    total = (
        await db.scalar(
            select(func.count())
            .select_from(SalesOrder)
            .where(*conditions)
        )
    ) or 0

    # 逾期天数 = 今天 - 下单日期（现款结算恒为 0）；按逾期天数倒序 => 非现款按日期升序，现款垫底
    stmt = (
        select(SalesOrder, Customer.name)
        .outerjoin(Customer, Customer.id == SalesOrder.customer_id)
        .where(*conditions)
        .order_by(
            (SalesOrder.settlement_method == "现款").asc(),
            SalesOrder.order_date.asc(),
            SalesOrder.id.asc(),
        )
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    )
    rows = (await db.execute(stmt)).all()
    items: list[ReceivableRow] = []
    for order, customer_name in rows:
        receivable = round(float(order.total_amount) - float(order.paid_amount), 2)
        days_overdue = (
            (today - order.order_date).days if order.settlement_method != "现款" else 0
        )
        items.append(
            ReceivableRow(
                customer_id=order.customer_id,
                customer_name=customer_name or "",
                order_id=order.id,
                order_no=order.order_no,
                order_date=order.order_date,
                total_amount=float(order.total_amount),
                paid_amount=float(order.paid_amount),
                receivable=receivable,
                settlement_method=order.settlement_method,
                days_overdue=days_overdue,
            )
        )
    return page_of(items, total, params.page, params.size)
