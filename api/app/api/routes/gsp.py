from datetime import date, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.core.storage import storage
from app.models.inventory import Batch
from app.models.master import (
    Certificate,
    CertificateAttachment,
    Customer,
    Manufacturer,
    Product,
    Supplier,
)
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.gsp import (
    BatchCreate,
    BatchOut,
    BatchUpdate,
    CertificateAttachmentOut,
    CertificateCreate,
    CertificateOut,
    CertificateUpdate,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]

# 证照扫描件允许的扩展名与大小上限
ATTACHMENT_SUFFIXES = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".doc", ".docx",
}
ATTACHMENT_MAX_BYTES = 20 * 1024 * 1024

# 证照对象类型 -> 主体模型
ENTITY_MODELS = {
    "customer": Customer,
    "supplier": Supplier,
    "product": Product,
    "manufacturer": Manufacturer,
}


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


@router.get("/certificates/expiring", response_model=Page[CertificateOut], summary="即将到期证照")
async def expiring_certificates(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    days: int = 90,
):
    deadline = date.today() + timedelta(days=days)
    stmt = (
        select(Certificate)
        .where(
            Certificate.valid_to.isnot(None),
            Certificate.valid_to <= deadline,
            Certificate.valid_to >= date.today(),
        )
        .order_by(Certificate.valid_to, Certificate.id)
    )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/certificates/{certificate_id}", response_model=CertificateOut, summary="证照详情")
async def get_certificate(certificate_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Certificate, certificate_id, "证照不存在")


@router.post("/certificates", response_model=CertificateOut, status_code=201, summary="创建证照")
async def create_certificate(payload: CertificateCreate, db: Db, _: CurrentUser):
    model = ENTITY_MODELS.get(payload.entity_type)
    if model is None:
        raise HTTPException(
            status_code=400,
            detail=f"未知的对象类型：{payload.entity_type}（可选 customer/supplier/product/manufacturer）",
        )
    if await db.get(model, payload.entity_id) is None:
        raise HTTPException(status_code=400, detail="证照关联的对象不存在")
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
    attachments = (
        await db.scalars(
            select(CertificateAttachment).where(
                CertificateAttachment.certificate_id == certificate_id
            )
        )
    ).all()
    for attachment in attachments:
        try:
            await storage.delete_object(attachment.object_key)
        except Exception:  # 存储不可用时不阻塞证照删除
            pass
        await db.delete(attachment)
    # 先落库删除子表记录，避免删除主表时触发外键约束
    await db.flush()
    await delete_and_commit(db, cert)
    return Message(message="证照已删除")


# ----------------------------- 证照附件（扫描件归档） -----------------------------
@router.get(
    "/certificates/{certificate_id}/attachments",
    response_model=list[CertificateAttachmentOut],
    summary="证照附件列表",
)
async def list_certificate_attachments(certificate_id: int, db: Db, _: CurrentUser):
    await get_or_404(db, Certificate, certificate_id, "证照不存在")
    rows = await db.scalars(
        select(CertificateAttachment)
        .where(CertificateAttachment.certificate_id == certificate_id)
        .order_by(CertificateAttachment.id)
    )
    return list(rows.all())


@router.post(
    "/certificates/{certificate_id}/attachments",
    response_model=CertificateAttachmentOut,
    status_code=201,
    summary="上传证照附件",
)
async def upload_certificate_attachment(
    certificate_id: int,
    db: Db,
    current: CurrentUser,
    file: Annotated[UploadFile, File(description="证照扫描件（pdf/图片/word）")],
):
    await get_or_404(db, Certificate, certificate_id, "证照不存在")
    file_name = file.filename or "未命名文件"
    suffix = Path(file_name).suffix.lower()
    if suffix not in ATTACHMENT_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{suffix or '未知'}（支持 PDF/图片/Word）",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(data) > ATTACHMENT_MAX_BYTES:
        raise HTTPException(status_code=400, detail="文件过大（上限 20MB）")

    object_key = f"gsp/certificates/{certificate_id}/{uuid4().hex}{suffix}"
    try:
        await storage.put_object(object_key, data, file.content_type)
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        raise HTTPException(status_code=503, detail=f"对象存储不可用：{exc}") from exc

    attachment = CertificateAttachment(
        certificate_id=certificate_id,
        file_name=file_name,
        object_key=object_key,
        content_type=file.content_type,
        size=len(data),
        uploaded_by=current.id,
    )
    return await create_and_commit(db, attachment)


@router.get("/attachments/{attachment_id}/download", summary="下载证照附件")
async def download_certificate_attachment(attachment_id: int, db: Db, _: CurrentUser):
    attachment = await get_or_404(db, CertificateAttachment, attachment_id, "附件不存在")
    try:
        data = await storage.get_object(attachment.object_key)
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        raise HTTPException(status_code=503, detail=f"对象存储不可用：{exc}") from exc
    return Response(
        content=data,
        media_type=attachment.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(attachment.file_name)}"
        },
    )


@router.delete("/attachments/{attachment_id}", response_model=Message, summary="删除证照附件")
async def delete_certificate_attachment(attachment_id: int, db: Db, _: CurrentUser):
    attachment = await get_or_404(db, CertificateAttachment, attachment_id, "附件不存在")
    try:
        await storage.delete_object(attachment.object_key)
    except Exception:  # 文件已丢失/存储不可用时仍清理记录
        pass
    await delete_and_commit(db, attachment)
    return Message(message="附件已删除")


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


@router.get("/batches/expiring", response_model=Page[BatchOut], summary="近效期批次")
async def expiring_batches(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    days: int = 180,
):
    deadline = date.today() + timedelta(days=days)
    stmt = (
        select(Batch)
        .where(
            Batch.expiry_date.isnot(None),
            Batch.expiry_date <= deadline,
        )
        .order_by(Batch.expiry_date, Batch.id)
    )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


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
