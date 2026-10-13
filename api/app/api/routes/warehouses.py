from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.models.master import Warehouse
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.master import WarehouseCreate, WarehouseOut, WarehouseUpdate

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
PERM_VIEW = Depends(require_permission("warehouse:view"))
PERM_MANAGE = Depends(require_permission("warehouse:manage"))


@router.get("", response_model=Page[WarehouseOut], summary="仓库列表", dependencies=[PERM_VIEW])
async def list_warehouses(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
    status: str | None = None,
):
    stmt = select(Warehouse).order_by(Warehouse.id)
    if keyword:
        stmt = stmt.where(
            Warehouse.name.ilike(f"%{keyword}%") | Warehouse.code.ilike(f"%{keyword}%")
        )
    if status:
        stmt = stmt.where(Warehouse.status == status)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/{warehouse_id}", response_model=WarehouseOut, summary="仓库详情", dependencies=[PERM_VIEW])
async def get_warehouse(warehouse_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Warehouse, warehouse_id, "仓库不存在")


@router.post("", response_model=WarehouseOut, status_code=201, summary="创建仓库", dependencies=[PERM_MANAGE])
async def create_warehouse(payload: WarehouseCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Warehouse).where(Warehouse.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="仓库编码已存在")
    return await create_and_commit(db, Warehouse(**payload.model_dump()))


@router.put("/{warehouse_id}", response_model=WarehouseOut, summary="更新仓库", dependencies=[PERM_MANAGE])
async def update_warehouse(warehouse_id: int, payload: WarehouseUpdate, db: Db, _: CurrentUser):
    warehouse = await get_or_404(db, Warehouse, warehouse_id, "仓库不存在")
    return await update_and_commit(db, warehouse, payload.model_dump(exclude_unset=True))


@router.delete("/{warehouse_id}", response_model=Message, summary="删除仓库", dependencies=[PERM_MANAGE])
async def delete_warehouse(warehouse_id: int, db: Db, _: CurrentUser):
    warehouse = await get_or_404(db, Warehouse, warehouse_id, "仓库不存在")
    await delete_and_commit(db, warehouse)
    return Message(message="仓库已删除")


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)
