from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.crud import (
    create_and_commit,
    delete_and_commit,
    get_or_404,
    like_contains,
    update_and_commit,
)
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.models.inventory import Inventory, InventoryMovement
from app.models.master import Product, Supplier, Warehouse
from app.models.purchase import PurchaseOrder, PurchaseOrderItem
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.purchase import (
    PurchaseOrderCreate,
    PurchaseOrderOut,
    PurchaseReceiveIn,
)
from app.services.gsp import assert_qualification, assert_qualifications

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
PERM_VIEW = Depends(require_permission("purchase:view"))
PERM_MANAGE = Depends(require_permission("purchase:manage"))


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)


async def _load_order(db: AsyncSession, order_id: int) -> PurchaseOrder:
    order = await db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product))
        .where(PurchaseOrder.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return order


async def _with_labels(db: AsyncSession, orders: list[PurchaseOrder]) -> list[PurchaseOrderOut]:
    """补齐供应商 / 仓库名称，避免前端列表先显示内部 ID 再被反查结果替换。"""
    if not orders:
        return []
    supplier_ids = {o.supplier_id for o in orders}
    warehouse_ids = {o.warehouse_id for o in orders}

    async def name_map(model, ids: set[int]) -> dict[int, str]:
        rows = await db.execute(select(model.id, model.name).where(model.id.in_(ids)))
        return dict(rows.all())

    supplier_names = await name_map(Supplier, supplier_ids)
    warehouse_names = await name_map(Warehouse, warehouse_ids)

    items: list[PurchaseOrderOut] = []
    for order in orders:
        item = PurchaseOrderOut.model_validate(order)
        item.supplier_name = supplier_names.get(order.supplier_id)
        item.warehouse_name = warehouse_names.get(order.warehouse_id)
        items.append(item)
    return items


@router.get("", response_model=Page[PurchaseOrderOut], summary="采购单列表", dependencies=[PERM_VIEW])
async def list_purchase_orders(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    order_no: str | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product))
        .order_by(PurchaseOrder.id.desc())
    )
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if warehouse_id is not None:
        stmt = stmt.where(PurchaseOrder.warehouse_id == warehouse_id)
    if order_no and order_no.strip():
        # 按采购单号查询，支持输入片段（粘贴完整单号或只打前几位）
        stmt = stmt.where(like_contains(PurchaseOrder.order_no, order_no))
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    if start_date:
        stmt = stmt.where(PurchaseOrder.order_date >= start_date)
    if end_date:
        stmt = stmt.where(PurchaseOrder.order_date <= end_date)
    rows, total = await _paginate(db, stmt, params)
    return page_of(await _with_labels(db, rows), total, params.page, params.size)


@router.get("/{order_id}", response_model=PurchaseOrderOut, summary="采购单详情", dependencies=[PERM_VIEW])
async def get_purchase_order(order_id: int, db: Db, _: CurrentUser):
    return (await _with_labels(db, [await _load_order(db, order_id)]))[0]


@router.post("", response_model=PurchaseOrderOut, status_code=201, summary="创建采购单", dependencies=[PERM_MANAGE])
async def create_purchase_order(payload: PurchaseOrderCreate, db: Db, current: CurrentUser):
    supplier = await get_or_404(db, Supplier, payload.supplier_id, "供应商不存在")
    await get_or_404(db, Warehouse, payload.warehouse_id, "仓库不存在")

    # GSP 首营企业与首营品种校验：供应商及采购商品资质不合规时禁止下单
    await assert_qualification(db, "supplier", supplier.id, "采购下单", current)
    await assert_qualifications(
        db,
        [("product", item.product_id) for item in payload.items],
        "采购下单",
        current,
    )

    order = PurchaseOrder(
        order_no=f"PENDING-{uuid4().hex[:12]}",
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        order_date=payload.order_date,
        expected_date=payload.expected_date,
        delivery_type=payload.delivery_type,
        remark=payload.remark,
        status="待收货",
    )
    db.add(order)
    await db.flush()
    order.order_no = f"PO{payload.order_date:%Y%m%d}{order.id:06d}"

    total = 0
    for item in payload.items:
        await get_or_404(db, Product, item.product_id, f"商品 {item.product_id} 不存在")
        amount = round(item.unit_cost * item.quantity, 2)
        total += amount
        db.add(
            PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                amount=amount,
            )
        )
    order.total_amount = round(total, 2)
    await db.commit()
    return (await _with_labels(db, [await _load_order(db, order.id)]))[0]


@router.put("/{order_id}", response_model=PurchaseOrderOut, summary="更新采购单", dependencies=[PERM_MANAGE])
async def update_purchase_order(
    order_id: int, payload: PurchaseOrderCreate, db: Db, _: CurrentUser
):
    order = await _load_order(db, order_id)
    if order.status == "已完成":
        raise HTTPException(status_code=400, detail="已完成的采购单不能修改")
    data = payload.model_dump(exclude={"items"})
    await update_and_commit(db, order, data)

    existing = {item.product_id: item for item in order.items}
    total = 0
    for item in payload.items:
        amount = round(item.unit_cost * item.quantity, 2)
        total += amount
        if item.product_id in existing:
            row = existing[item.product_id]
            row.quantity = item.quantity
            row.unit_cost = item.unit_cost
            row.amount = amount
        else:
            db.add(
                PurchaseOrderItem(
                    purchase_order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    amount=amount,
                )
            )
    order.total_amount = round(total, 2)
    await db.commit()
    return (await _with_labels(db, [await _load_order(db, order.id)]))[0]


@router.delete("/{order_id}", response_model=Message, summary="删除采购单", dependencies=[PERM_MANAGE])
async def delete_purchase_order(order_id: int, db: Db, _: CurrentUser):
    order = await _load_order(db, order_id)
    if order.status != "待收货":
        raise HTTPException(status_code=400, detail="仅待收货状态的采购单可删除")
    await delete_and_commit(db, order)
    return Message(message="采购单已删除")


@router.post("/{order_id}/receive", response_model=PurchaseOrderOut, summary="采购收货", dependencies=[PERM_MANAGE])
async def receive_purchase_order(
    order_id: int, payload: PurchaseReceiveIn, db: Db, current: CurrentUser
):
    order = await _load_order(db, order_id)
    if order.status == "已完成":
        raise HTTPException(status_code=400, detail="采购单已完成，不能再收货")

    items_by_id = {item.id: item for item in order.items}
    # GSP 收货准入校验：供应商资质不合规时不得收货入库
    await assert_qualification(db, "supplier", order.supplier_id, "采购收货", current)
    for recv in payload.items:
        item = items_by_id.get(recv.item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"明细 {recv.item_id} 不存在")
        if recv.received_quantity > item.quantity - item.received_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"明细 {item.id} 实收数量超过剩余应收数量",
            )
        item.received_quantity += recv.received_quantity
        item.received_date = payload.received_date
        await _stock_in(db, order.warehouse_id, item.product_id, recv.received_quantity)
        db.add(
            InventoryMovement(
                warehouse_id=order.warehouse_id,
                product_id=item.product_id,
                movement_type="采购入库",
                quantity=recv.received_quantity,
                movement_date=payload.received_date,
                ref_table="purchase_order_item",
                ref_id=item.id,
                created_by=current.id,
                remark=order.order_no,
            )
        )

    if all(i.received_quantity >= i.quantity for i in order.items):
        order.status = "已完成"
        order.received_date = payload.received_date
    elif any(i.received_quantity > 0 for i in order.items):
        order.status = "部分收货"
    await db.commit()
    return (await _with_labels(db, [await _load_order(db, order.id)]))[0]


async def _stock_in(db: AsyncSession, warehouse_id: int, product_id: int, quantity: int) -> None:
    inv = await db.scalar(
        select(Inventory).where(
            Inventory.warehouse_id == warehouse_id,
            Inventory.product_id == product_id,
        )
    )
    if inv is None:
        product = await get_or_404(db, Product, product_id, "商品不存在")
        db.add(
            Inventory(
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=quantity,
                safety_stock=0,
            )
        )
    else:
        inv.quantity += quantity
