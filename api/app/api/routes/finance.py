from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, paginate_query
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.finance import PaymentRecord
from app.models.master import Customer
from app.models.sales import SalesOrder
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.finance import PaymentCreate, PaymentOut, ReceivableRow

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/payments", response_model=Page[PaymentOut], summary="收款记录列表")
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


@router.get("/payments/{payment_id}", response_model=PaymentOut, summary="收款记录详情")
async def get_payment(payment_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, PaymentRecord, payment_id, "收款记录不存在")


@router.post("/payments", response_model=PaymentOut, status_code=201, summary="登记收款")
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


@router.delete("/payments/{payment_id}", response_model=Message, summary="删除收款记录")
async def delete_payment(payment_id: int, db: Db, _: CurrentUser):
    payment = await get_or_404(db, PaymentRecord, payment_id, "收款记录不存在")
    await delete_and_commit(db, payment)
    return Message(message="收款记录已删除")


@router.get("/receivables", response_model=list[ReceivableRow], summary="应收账龄分析")
async def list_receivables(
    db: Db,
    _: CurrentUser,
    as_of: date | None = None,
    customer_id: int | None = None,
):
    today = as_of or date.today()
    stmt = select(SalesOrder).where(SalesOrder.status != "已取消")
    if customer_id is not None:
        stmt = stmt.where(SalesOrder.customer_id == customer_id)
    orders = (await db.scalars(stmt)).all()
    result: list[ReceivableRow] = []
    for order in orders:
        receivable = float(order.total_amount) - float(order.paid_amount)
        if receivable <= 1e-6:
            continue
        customer = await db.get(Customer, order.customer_id)
        days_overdue = (today - order.order_date).days if order.settlement_method != "现款" else 0
        result.append(
            ReceivableRow(
                customer_id=order.customer_id,
                customer_name=customer.name if customer else "",
                order_id=order.id,
                order_no=order.order_no,
                order_date=order.order_date,
                total_amount=float(order.total_amount),
                paid_amount=float(order.paid_amount),
                receivable=round(receivable, 2),
                settlement_method=order.settlement_method,
                days_overdue=days_overdue,
            )
        )
    result.sort(key=lambda r: r.days_overdue, reverse=True)
    return result
