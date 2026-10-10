from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.crud import delete_and_commit, get_or_404, paginate_query
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.api.routes.reports import invalidate_product_summary_cache
from app.core.database import get_db
from app.models.inventory import Inventory, InventoryMovement
from app.models.master import Customer, Product, Warehouse
from app.models.org import Employee
from app.models.sales import SalesOrder, SalesOrderItem
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.sales import SalesOrderCreate, SalesOrderOut, ShipRequest
from app.services.gsp import assert_qualification, assert_qualifications

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
PERM_VIEW = Depends(require_permission("sales:view"))
PERM_MANAGE = Depends(require_permission("sales:manage"))


async def _load_order(db: AsyncSession, order_id: int) -> SalesOrder:
    order = await db.scalar(
        select(SalesOrder)
        .options(selectinload(SalesOrder.items).selectinload(SalesOrderItem.product))
        .where(SalesOrder.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="销售订单不存在")
    return order


async def _with_labels(db: AsyncSession, orders: list[SalesOrder]) -> list[SalesOrderOut]:
    """补齐客户/销售员/仓库名称，避免前端列表先显示内部 ID 再被反查结果替换。"""
    if not orders:
        return []
    customer_ids = {o.customer_id for o in orders}
    employee_ids = {o.employee_id for o in orders}
    warehouse_ids = {o.warehouse_id for o in orders}

    async def name_map(model, ids: set[int]) -> dict[int, str]:
        rows = await db.execute(select(model.id, model.name).where(model.id.in_(ids)))
        return dict(rows.all())

    customer_names = await name_map(Customer, customer_ids)
    employee_names = await name_map(Employee, employee_ids)
    warehouse_names = await name_map(Warehouse, warehouse_ids)

    items: list[SalesOrderOut] = []
    for order in orders:
        item = SalesOrderOut.model_validate(order)
        item.customer_name = customer_names.get(order.customer_id)
        item.employee_name = employee_names.get(order.employee_id)
        item.warehouse_name = warehouse_names.get(order.warehouse_id)
        items.append(item)
    return items


@router.get("", response_model=Page[SalesOrderOut], summary="销售订单列表", dependencies=[PERM_VIEW])
async def list_sales_orders(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    customer_id: int | None = None,
    employee_id: int | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = (
        select(SalesOrder)
        .options(selectinload(SalesOrder.items).selectinload(SalesOrderItem.product))
        .order_by(SalesOrder.id.desc())
    )
    if customer_id is not None:
        stmt = stmt.where(SalesOrder.customer_id == customer_id)
    if employee_id is not None:
        stmt = stmt.where(SalesOrder.employee_id == employee_id)
    if status:
        stmt = stmt.where(SalesOrder.status == status)
    if start_date:
        stmt = stmt.where(SalesOrder.order_date >= start_date)
    if end_date:
        stmt = stmt.where(SalesOrder.order_date <= end_date)
    rows, total = await paginate_query(db, stmt, params.page, params.size)
    return page_of(await _with_labels(db, rows), total, params.page, params.size)


@router.get("/{order_id}", response_model=SalesOrderOut, summary="销售订单详情", dependencies=[PERM_VIEW])
async def get_sales_order(order_id: int, db: Db, _: CurrentUser):
    return (await _with_labels(db, [await _load_order(db, order_id)]))[0]


@router.post("", response_model=SalesOrderOut, status_code=201, summary="创建销售订单", dependencies=[PERM_MANAGE])
async def create_sales_order(payload: SalesOrderCreate, db: Db, current: CurrentUser):
    customer = await get_or_404(db, Customer, payload.customer_id, "客户不存在")
    if customer.status != "正常":
        raise HTTPException(status_code=400, detail=f"客户状态为「{customer.status}」，不能下单")
    await get_or_404(db, Employee, payload.employee_id, "销售员不存在")
    await get_or_404(db, Warehouse, payload.warehouse_id, "仓库不存在")

    # GSP 交易准入校验：客户及其订购商品的资质档案必须合规（在任何写库动作之前）
    await assert_qualification(db, "customer", payload.customer_id, "下单", current)
    await assert_qualifications(
        db,
        [("product", item.product_id) for item in payload.items],
        "下单",
        current,
    )

    order = SalesOrder(
        order_no=f"PENDING-{uuid4().hex[:12]}",
        customer_id=payload.customer_id,
        employee_id=payload.employee_id,
        warehouse_id=payload.warehouse_id,
        order_date=payload.order_date,
        status="待付款",
        shipping_address=payload.shipping_address,
        invoice_type=payload.invoice_type,
        settlement_method=payload.settlement_method,
        delivery_type=payload.delivery_type,
        delivery_date=payload.delivery_date,
        remark=payload.remark,
    )
    db.add(order)
    await db.flush()
    order.order_no = f"SO{payload.order_date:%Y%m%d}{order.id:06d}"

    subtotal = discount_total = cost_total = 0
    quantity_total = 0
    for item in payload.items:
        product = await get_or_404(db, Product, item.product_id, f"商品 {item.product_id} 不存在")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"商品「{product.name}」已下架")
        line_subtotal = round(float(product.standard_price) * item.quantity, 2)
        line_discount = round(line_subtotal * item.discount_rate, 2)
        line_amount = round(line_subtotal - line_discount, 2)
        subtotal += line_subtotal
        discount_total += line_discount
        cost_total += round(product.cost_price * item.quantity, 2)
        quantity_total += item.quantity
        db.add(
            SalesOrderItem(
                sales_order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=product.standard_price,
                unit_cost=product.cost_price,
                discount_rate=item.discount_rate,
                discount_amount=line_discount,
                amount=line_amount,
            )
        )

    order.item_count = len(payload.items)
    order.total_quantity = quantity_total
    order.subtotal_amount = round(subtotal, 2)
    order.discount_amount = round(discount_total, 2)
    order.total_amount = round(subtotal - discount_total, 2)
    order.cost_amount = round(cost_total, 2)
    await db.commit()
    invalidate_product_summary_cache()
    return (await _with_labels(db, [await _load_order(db, order.id)]))[0]


@router.delete("/{order_id}", response_model=Message, summary="删除销售订单", dependencies=[PERM_MANAGE])
async def delete_sales_order(order_id: int, db: Db, _: CurrentUser):
    order = await _load_order(db, order_id)
    if order.status not in ("待付款",):
        raise HTTPException(status_code=400, detail="仅待付款状态的订单可删除")
    await delete_and_commit(db, order)
    invalidate_product_summary_cache()
    return Message(message="销售订单已删除")


@router.post("/{order_id}/ship", response_model=SalesOrderOut, summary="销售发货出库", dependencies=[PERM_MANAGE])
async def ship_sales_order(order_id: int, payload: ShipRequest, db: Db, current: CurrentUser):
    order = await _load_order(db, order_id)
    if order.status == "已取消":
        raise HTTPException(status_code=400, detail="已取消订单不能发货")
    if order.status == "已完成":
        raise HTTPException(status_code=400, detail="订单已完成，不能重复发货")
    if order.delivery_date is not None:
        raise HTTPException(status_code=400, detail="订单已发货，不能重复发货")

    # GSP 交易准入校验：发货时再次核对客户与商品资质，避免下单后证照过期仍出库
    await assert_qualification(db, "customer", order.customer_id, "发货", current)
    await assert_qualifications(
        db,
        [("product", item.product_id) for item in order.items],
        "发货",
        current,
    )

    for item in order.items:
        inv = await db.scalar(
            select(Inventory).where(
                Inventory.warehouse_id == order.warehouse_id,
                Inventory.product_id == item.product_id,
            )
        )
        stock = inv.quantity if inv else 0
        if stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"商品 {item.product_id} 库存不足（当前 {stock}，需要 {item.quantity}）",
            )

    for item in order.items:
        inv = await db.scalar(
            select(Inventory).where(
                Inventory.warehouse_id == order.warehouse_id,
                Inventory.product_id == item.product_id,
            )
        )
        inv.quantity -= item.quantity
        db.add(
            InventoryMovement(
                warehouse_id=order.warehouse_id,
                product_id=item.product_id,
                movement_type="销售出库",
                quantity=-item.quantity,
                movement_date=payload.delivery_date,
                ref_table="sales_order_item",
                ref_id=item.id,
                created_by=current.id,
                remark=order.order_no,
            )
        )

    order.delivery_date = payload.delivery_date
    order.status = "已发货" if order.paid_amount < order.total_amount else "已完成"
    await db.commit()
    return (await _with_labels(db, [await _load_order(db, order.id)]))[0]


@router.post("/{order_id}/cancel", response_model=SalesOrderOut, summary="取消销售订单", dependencies=[PERM_MANAGE])
async def cancel_sales_order(order_id: int, db: Db, _: CurrentUser):
    order = await _load_order(db, order_id)
    if order.delivery_date is not None:
        raise HTTPException(status_code=400, detail="已发货订单不能取消，请走退货流程")
    order.status = "已取消"
    await db.commit()
    invalidate_product_summary_cache()
    return (await _with_labels(db, [await _load_order(db, order.id)]))[0]
