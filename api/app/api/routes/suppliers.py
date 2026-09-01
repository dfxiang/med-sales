from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.master import Supplier
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.master import SupplierCreate, SupplierOut, SupplierUpdate

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Page[SupplierOut], summary="供应商列表")
async def list_suppliers(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
    status: str | None = None,
):
    stmt = select(Supplier).order_by(Supplier.id)
    if keyword:
        stmt = stmt.where(
            Supplier.name.ilike(f"%{keyword}%") | Supplier.code.ilike(f"%{keyword}%")
        )
    if status:
        stmt = stmt.where(Supplier.status == status)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/{supplier_id}", response_model=SupplierOut, summary="供应商详情")
async def get_supplier(supplier_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Supplier, supplier_id, "供应商不存在")


@router.post("", response_model=SupplierOut, status_code=201, summary="创建供应商")
async def create_supplier(payload: SupplierCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Supplier).where(Supplier.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="供应商编码已存在")
    return await create_and_commit(db, Supplier(**payload.model_dump()))


@router.put("/{supplier_id}", response_model=SupplierOut, summary="更新供应商")
async def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Db, _: CurrentUser):
    supplier = await get_or_404(db, Supplier, supplier_id, "供应商不存在")
    return await update_and_commit(db, supplier, payload.model_dump(exclude_unset=True))


@router.delete("/{supplier_id}", response_model=Message, summary="删除供应商")
async def delete_supplier(supplier_id: int, db: Db, _: CurrentUser):
    supplier = await get_or_404(db, Supplier, supplier_id, "供应商不存在")
    await delete_and_commit(db, supplier)
    return Message(message="供应商已删除")


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)
