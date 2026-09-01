from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, paginate_query
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.inventory import Inventory, InventoryMovement
from app.models.master import Product
from app.models.returns import SalesReturn, SalesReturnItem
from app.models.sales import SalesOrder
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.returns import SalesReturnCreate, SalesReturnOut

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


async def _load_return(db: AsyncSession, return_id: int) -> SalesReturn:
    obj = await db.scalar(
        select(SalesReturn)
        .options(selectinload(SalesReturn.items))
        .where(SalesReturn.id == return_id)
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="退货单不存在")
    return obj


@router.get("", response_model=Page[SalesReturnOut], summary="退货单列表")
async def list_returns(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    customer_id: int | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = (
        select(SalesReturn)
        .options(selectinload(SalesReturn.items))
        .order_by(SalesReturn.id.desc())
    )
    if customer_id is not None:
        stmt = stmt.where(SalesReturn.customer_id == customer_id)
    if status:
        stmt = stmt.where(SalesReturn.status == status)
    if start_date:
        stmt = stmt.where(SalesReturn.return_date >= start_date)
    if end_date:
        stmt = stmt.where(SalesReturn.return_date <= end_date)
    rows, total = await paginate_query(db, stmt, params.page, params.size)
    return page_of(rows, total, params.page, params.size)


@router.get("/{return_id}", response_model=SalesReturnOut, summary="退货单详情")
async def get_return(return_id: int, db: Db, _: CurrentUser):
    return await _load_return(db, return_id)


@router.post("", response_model=SalesReturnOut, status_code=201, summary="创建退货单")
async def create_return(payload: SalesReturnCreate, db: Db, _: CurrentUser):
    order = await db.get(SalesOrder, payload.sales_order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="原销售订单不存在")

    obj = SalesReturn(
        return_no=f"PENDING-{uuid4().hex[:12]}",
        sales_order_id=payload.sales_order_id,
        customer_id=order.customer_id,
        warehouse_id=order.warehouse_id,
        return_date=payload.return_date,
        status="待处理",
        reason=payload.reason,
        remark=payload.remark or f"原订单 {order.order_no}",
    )
    db.add(obj)
    await db.flush()
    obj.return_no = f"RT{payload.return_date:%Y%m%d}{obj.id:06d}"

    total = 0
    for item in payload.items:
        await get_or_404(db, Product, item.product_id, f"商品 {item.product_id} 不存在")
        amount = round(item.unit_price * item.quantity, 2)
        total += amount
        db.add(
            SalesReturnItem(
                sales_return_id=obj.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=amount,
                reason=item.reason or payload.reason,
            )
        )
    obj.total_amount = round(total, 2)
    await db.commit()
    return await _load_return(db, obj.id)


@router.delete("/{return_id}", response_model=Message, summary="删除退货单")
async def delete_return(return_id: int, db: Db, _: CurrentUser):
    obj = await _load_return(db, return_id)
    if obj.status == "已完成":
        raise HTTPException(status_code=400, detail="已完成的退货单不能删除")
    await delete_and_commit(db, obj)
    return Message(message="退货单已删除")


@router.post("/{return_id}/process", response_model=SalesReturnOut, summary="处理退货并入库")
async def process_return(return_id: int, db: Db, current: CurrentUser):
    obj = await _load_return(db, return_id)
    if obj.status == "已完成":
        raise HTTPException(status_code=400, detail="退货单已处理")
    for item in obj.items:
        inv = await db.scalar(
            select(Inventory).where(
                Inventory.warehouse_id == obj.warehouse_id,
                Inventory.product_id == item.product_id,
            )
        )
        if inv is None:
            db.add(
                Inventory(
                    warehouse_id=obj.warehouse_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    safety_stock=0,
                )
            )
        else:
            inv.quantity += item.quantity
        db.add(
            InventoryMovement(
                warehouse_id=obj.warehouse_id,
                product_id=item.product_id,
                movement_type="退货入库",
                quantity=item.quantity,
                movement_date=obj.return_date,
                ref_table="sales_return_item",
                ref_id=item.id,
                created_by=current.id,
                remark=obj.return_no,
            )
        )
    obj.status = "已完成"
    await db.commit()
    return await _load_return(db, obj.id)
