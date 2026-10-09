from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import get_or_404, paginate_query
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.inventory import Inventory, InventoryMovement
from app.models.master import Product, ProductCategory, Warehouse
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.inventory import (
    InventoryMovementOut,
    InventoryOut,
    OpenStockRequest,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


def stock_status(quantity: int, safety_stock: int) -> str:
    if quantity < safety_stock:
        return "库存不足"
    if quantity <= safety_stock * 1.2:
        return "库存预警"
    return "库存充足"


# 与 stock_status() 保持一致的 SQL 表达式，用于在数据库层过滤/计数
STOCK_STATUS_EXPR = case(
    (Inventory.quantity < Inventory.safety_stock, "库存不足"),
    (Inventory.quantity <= Inventory.safety_stock * 1.2, "库存预警"),
    else_="库存充足",
)


@router.get("", response_model=Page[InventoryOut], summary="库存列表（含状态）")
async def list_inventory(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    warehouse_id: int | None = None,
    product_id: int | None = None,
    status: str | None = None,
):
    stmt = select(Inventory).order_by(Inventory.id)
    if warehouse_id is not None:
        stmt = stmt.where(Inventory.warehouse_id == warehouse_id)
    if product_id is not None:
        stmt = stmt.where(Inventory.product_id == product_id)
    if status:
        stmt = stmt.where(STOCK_STATUS_EXPR == status)
    rows, total = await paginate_query(db, stmt, params.page, params.size)
    result = []
    for inv in rows:
        product = await db.get(Product, inv.product_id)
        warehouse = await db.get(Warehouse, inv.warehouse_id)
        category = (
            await db.get(ProductCategory, product.category_id)
            if product and product.category_id
            else None
        )
        s = stock_status(inv.quantity, inv.safety_stock)
        result.append(
            InventoryOut(
                id=inv.id,
                warehouse_id=inv.warehouse_id,
                product_id=inv.product_id,
                quantity=inv.quantity,
                safety_stock=inv.safety_stock,
                updated_at=inv.updated_at,
                warehouse_name=warehouse.name if warehouse else None,
                product_name=product.name if product else None,
                sku=product.sku if product else None,
                category_name=category.name if category else None,
                stock_status=s,
                stock_value=round(inv.quantity * float(product.cost_price), 2)
                if product
                else None,
            )
        )
    return page_of(result, total, params.page, params.size)


@router.get("/movements", response_model=Page[InventoryMovementOut], summary="库存流水列表")
async def list_movements(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    warehouse_id: int | None = None,
    product_id: int | None = None,
    movement_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = select(InventoryMovement).order_by(InventoryMovement.id.desc())
    if warehouse_id is not None:
        stmt = stmt.where(InventoryMovement.warehouse_id == warehouse_id)
    if product_id is not None:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    if movement_type:
        stmt = stmt.where(InventoryMovement.movement_type == movement_type)
    if start_date:
        stmt = stmt.where(InventoryMovement.movement_date >= start_date)
    if end_date:
        stmt = stmt.where(InventoryMovement.movement_date <= end_date)
    rows, total = await paginate_query(db, stmt, params.page, params.size)
    return page_of(rows, total, params.page, params.size)


@router.get("/movements/{movement_id}", response_model=InventoryMovementOut, summary="库存流水详情")
async def get_movement(movement_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, InventoryMovement, movement_id, "流水不存在")


@router.get("/{inventory_id}", response_model=InventoryOut, summary="库存详情")
async def get_inventory(inventory_id: int, db: Db, _: CurrentUser):
    inv = await get_or_404(db, Inventory, inventory_id, "库存记录不存在")
    product = await db.get(Product, inv.product_id)
    warehouse = await db.get(Warehouse, inv.warehouse_id)
    return InventoryOut(
        id=inv.id,
        warehouse_id=inv.warehouse_id,
        product_id=inv.product_id,
        quantity=inv.quantity,
        safety_stock=inv.safety_stock,
        updated_at=inv.updated_at,
        warehouse_name=warehouse.name if warehouse else None,
        product_name=product.name if product else None,
        sku=product.sku if product else None,
        stock_status=stock_status(inv.quantity, inv.safety_stock),
        stock_value=round(inv.quantity * float(product.cost_price), 2)
        if product
        else None,
    )


@router.post("/open-stock", response_model=Message, status_code=201, summary="期初建账入库")
async def open_stock(payload: OpenStockRequest, db: Db, current: CurrentUser):
    await get_or_404(db, Warehouse, payload.warehouse_id, "仓库不存在")
    for item in payload.items:
        product = await get_or_404(db, Product, item.product_id, f"商品 {item.product_id} 不存在")
        inv = await db.scalar(
            select(Inventory).where(
                Inventory.warehouse_id == payload.warehouse_id,
                Inventory.product_id == item.product_id,
            )
        )
        if inv is None:
            db.add(
                Inventory(
                    warehouse_id=payload.warehouse_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    safety_stock=0,
                )
            )
        else:
            inv.quantity += item.quantity
        db.add(
            InventoryMovement(
                warehouse_id=payload.warehouse_id,
                product_id=item.product_id,
                movement_type="期初入库",
                quantity=item.quantity,
                movement_date=payload.movement_date,
                created_by=current.id,
                remark=f"期初建账 {product.sku}",
            )
        )
    await db.commit()
    return Message(message="期初入库完成")
