from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.models.inventory import Batch
from app.models.master import Certificate
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.gsp import (
    BatchCreate,
    BatchOut,
    BatchUpdate,
    CertificateCreate,
    CertificateOut,
    CertificateUpdate,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)


# ----------------------------- 证照管理 -----------------------------
@router.get("/certificates", response_model=Page[CertificateOut], summary="证照列表")
async def list_certificates(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    entity_type: str | None = None,
    entity_id: int | None = None,
    status: str | None = None,
):
    stmt = select(Certificate).order_by(Certificate.id)
    if entity_type:
        stmt = stmt.where(Certificate.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Certificate.entity_id == entity_id)
    if status:
        stmt = stmt.where(Certificate.status == status)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/certificates/expiring", response_model=list[CertificateOut], summary="即将到期证照")
async def expiring_certificates(
    db: Db,
    _: CurrentUser,
    days: int = 90,
):
    deadline = date.today() + timedelta(days=days)
    stmt = select(Certificate).where(
        Certificate.valid_to.isnot(None),
        Certificate.valid_to <= deadline,
        Certificate.valid_to >= date.today(),
    )
    return list((await db.scalars(stmt)).all())


@router.get("/certificates/{certificate_id}", response_model=CertificateOut, summary="证照详情")
async def get_certificate(certificate_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Certificate, certificate_id, "证照不存在")


@router.post("/certificates", response_model=CertificateOut, status_code=201, summary="创建证照")
async def create_certificate(payload: CertificateCreate, db: Db, _: CurrentUser):
    return await create_and_commit(db, Certificate(**payload.model_dump()))


@router.put("/certificates/{certificate_id}", response_model=CertificateOut, summary="更新证照")
async def update_certificate(
    certificate_id: int, payload: CertificateUpdate, db: Db, _: CurrentUser
):
    cert = await get_or_404(db, Certificate, certificate_id, "证照不存在")
    return await update_and_commit(db, cert, payload.model_dump(exclude_unset=True))


@router.delete("/certificates/{certificate_id}", response_model=Message, summary="删除证照")
async def delete_certificate(certificate_id: int, db: Db, _: CurrentUser):
    cert = await get_or_404(db, Certificate, certificate_id, "证照不存在")
    await delete_and_commit(db, cert)
    return Message(message="证照已删除")


# ----------------------------- 批次/效期管理 -----------------------------
@router.get("/batches", response_model=Page[BatchOut], summary="批次列表")
async def list_batches(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    product_id: int | None = None,
    status: str | None = None,
):
    stmt = select(Batch).order_by(Batch.id)
    if product_id is not None:
        stmt = stmt.where(Batch.product_id == product_id)
    if status:
        stmt = stmt.where(Batch.status == status)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/batches/expiring", response_model=list[BatchOut], summary="近效期批次")
async def expiring_batches(
    db: Db,
    _: CurrentUser,
    days: int = 180,
):
    deadline = date.today() + timedelta(days=days)
    stmt = select(Batch).where(
        Batch.expiry_date.isnot(None),
        Batch.expiry_date <= deadline,
    )
    return list((await db.scalars(stmt)).all())


@router.get("/batches/{batch_id}", response_model=BatchOut, summary="批次详情")
async def get_batch(batch_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Batch, batch_id, "批次不存在")


@router.post("/batches", response_model=BatchOut, status_code=201, summary="创建批次")
async def create_batch(payload: BatchCreate, db: Db, _: CurrentUser):
    from app.models.master import Product

    await get_or_404(db, Product, payload.product_id, "商品不存在")
    return await create_and_commit(db, Batch(**payload.model_dump()))


@router.put("/batches/{batch_id}", response_model=BatchOut, summary="更新批次")
async def update_batch(batch_id: int, payload: BatchUpdate, db: Db, _: CurrentUser):
    batch = await get_or_404(db, Batch, batch_id, "批次不存在")
    return await update_and_commit(db, batch, payload.model_dump(exclude_unset=True))


@router.delete("/batches/{batch_id}", response_model=Message, summary="删除批次")
async def delete_batch(batch_id: int, db: Db, _: CurrentUser):
    batch = await get_or_404(db, Batch, batch_id, "批次不存在")
    await delete_and_commit(db, batch)
    return Message(message="批次已删除")
