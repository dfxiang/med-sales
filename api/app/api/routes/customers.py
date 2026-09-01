from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.master import Customer
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.master import CustomerCreate, CustomerOut, CustomerUpdate

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Page[CustomerOut], summary="客户列表")
async def list_customers(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
    customer_type: str | None = None,
    coop_level: str | None = None,
    status: str | None = None,
    province: str | None = None,
):
    stmt = select(Customer).order_by(Customer.id)
    if keyword:
        stmt = stmt.where(
            Customer.name.ilike(f"%{keyword}%") | Customer.code.ilike(f"%{keyword}%")
        )
    if customer_type:
        stmt = stmt.where(Customer.customer_type == customer_type)
    if coop_level:
        stmt = stmt.where(Customer.coop_level == coop_level)
    if status:
        stmt = stmt.where(Customer.status == status)
    if province:
        stmt = stmt.where(Customer.province == province)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/{customer_id}", response_model=CustomerOut, summary="客户详情")
async def get_customer(customer_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Customer, customer_id, "客户不存在")


@router.post("", response_model=CustomerOut, status_code=201, summary="创建客户")
async def create_customer(payload: CustomerCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Customer).where(Customer.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="客户编码已存在")
    return await create_and_commit(db, Customer(**payload.model_dump()))


@router.put("/{customer_id}", response_model=CustomerOut, summary="更新客户")
async def update_customer(customer_id: int, payload: CustomerUpdate, db: Db, _: CurrentUser):
    customer = await get_or_404(db, Customer, customer_id, "客户不存在")
    return await update_and_commit(db, customer, payload.model_dump(exclude_unset=True))


@router.delete("/{customer_id}", response_model=Message, summary="删除客户")
async def delete_customer(customer_id: int, db: Db, _: CurrentUser):
    customer = await get_or_404(db, Customer, customer_id, "客户不存在")
    await delete_and_commit(db, customer)
    return Message(message="客户已删除")


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)
