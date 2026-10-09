import mimetypes
from datetime import date, datetime, timedelta
from dataclasses import asdict
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import and_, func, literal, select, union_all, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.config import settings
from app.core.database import get_db
from app.core.storage import storage
from app.models.inventory import Batch
from app.models.master import Certificate, CertificateAttachment, Product
from app.models.system import AuditLog
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.gsp import (
    BatchCreate,
    BatchOut,
    BatchUpdate,
    CertificateAttachmentOut,
    CertificateCreate,
    CertificateOut,
    CertificateReviewIn,
    CertificateUpdate,
    GspAlertOut,
    GspAlertSummaryOut,
    QualificationOut,
    QualificationIssueOut,
)
from app.services.gsp import (
    ENTITY_LABELS,
    ENTITY_MODELS,
    REVIEW_APPROVED,
    REVIEW_PENDING,
    REVIEW_REJECTED,
    check_qualification,
    days_to_expiry,
    effective_status,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]

# 证照扫描件允许的扩展名与大小上限
ATTACHMENT_SUFFIXES = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".doc", ".docx",
}
ATTACHMENT_MAX_BYTES = 20 * 1024 * 1024

# 浏览器可原生渲染（在线预览）的扫描件类型
PREVIEW_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

# 到期预警分级（互斥区间，天）
ALERT_LEVELS = ("已过期", "30天内", "60天内", "90天内")


def attachment_kind(file_name: str) -> str:
    """扫描件预览形态：pdf / image / other。"""
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in PREVIEW_IMAGE_SUFFIXES:
        return "image"
    return "other"


def attachment_media_type(file_name: str, content_type: str | None) -> str:
    """推断响应的 MIME 类型。

    扫描件上传时由浏览器带上 Content-Type；历史数据缺失时按扩展名兜底，
    否则响应会退回 application/octet-stream，浏览器就会变成下载而不是预览。
    """
    if Path(file_name).suffix.lower() == ".pdf":
        return "application/pdf"
    if content_type and content_type != "application/octet-stream":
        return content_type
    return mimetypes.guess_type(file_name)[0] or "application/octet-stream"


def _attachment_out(attachment: CertificateAttachment) -> CertificateAttachmentOut:
    item = CertificateAttachmentOut.model_validate(attachment)
    item.kind = attachment_kind(attachment.file_name)
    item.media_type = attachment_media_type(attachment.file_name, attachment.content_type)
    item.previewable = item.kind != "other"
    return item


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)


async def _entity_name_map(
    db: AsyncSession, pairs: set[tuple[str, int]]
) -> dict[tuple[str, int], str]:
    """批量解析证照主体名称，避免逐行查询。"""
    names: dict[tuple[str, int], str] = {}
    for entity_type, model in ENTITY_MODELS.items():
        ids = {entity_id for et, entity_id in pairs if et == entity_type}
        if not ids:
            continue
        rows = (
            await db.execute(select(model.id, model.name).where(model.id.in_(ids)))
        ).all()
        for row_id, name in rows:
            names[(entity_type, row_id)] = name
    return names


async def _decorate_certificates(
    db: AsyncSession, certs: list[Certificate]
) -> list[CertificateOut]:
    """补充主体名称、附件数、有效期状态等派生字段。"""
    if not certs:
        return []
    cert_ids = [c.id for c in certs]
    counts = dict(
        (
            await db.execute(
                select(
                    CertificateAttachment.certificate_id,
                    func.count(CertificateAttachment.id),
                )
                .where(CertificateAttachment.certificate_id.in_(cert_ids))
                .group_by(CertificateAttachment.certificate_id)
            )
        ).all()
    )
    names = await _entity_name_map(
        db, {(c.entity_type, c.entity_id) for c in certs}
    )
    today = date.today()
    out: list[CertificateOut] = []
    for cert in certs:
        item = CertificateOut.model_validate(cert)
        item.entity_name = names.get((cert.entity_type, cert.entity_id))
        item.effective_status = effective_status(cert, today)
        item.days_to_expiry = days_to_expiry(cert, today)
        item.attachment_count = int(counts.get(cert.id, 0))
        out.append(item)
    return out


async def _load_certificate_out(db: AsyncSession, certificate_id: int) -> CertificateOut:
    cert = await get_or_404(db, Certificate, certificate_id, "证照不存在")
    return (await _decorate_certificates(db, [cert]))[0]


def _alert_bucket(column, level: str, today: date, days: int):
    """构造互斥的到期分级条件。"""
    if level == "已过期":
        return column < today
    if level == "30天内":
        return and_(column >= today, column <= today + timedelta(days=30))
    if level == "60天内":
        return and_(
            column > today + timedelta(days=30), column <= today + timedelta(days=60)
        )
    if level == "90天内":
        return and_(
            column > today + timedelta(days=60), column <= today + timedelta(days=90)
        )
    return and_(column <= today + timedelta(days=days))


def _level_of(days_left: int) -> str:
    if days_left < 0:
        return "已过期"
    if days_left <= 30:
        return "30天内"
    if days_left <= 60:
        return "60天内"
    return "90天内"


# ----------------------------- 证照管理 -----------------------------
@router.get("/certificates", response_model=Page[CertificateOut], summary="证照列表")
async def list_certificates(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    entity_type: str | None = None,
    entity_id: int | None = None,
    status: str | None = None,
    review_status: str | None = None,
    keyword: str | None = None,
):
    stmt = select(Certificate).order_by(Certificate.valid_to, Certificate.id)
    if entity_type:
        stmt = stmt.where(Certificate.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(Certificate.entity_id == entity_id)
    if status:
        stmt = stmt.where(Certificate.status == status)
    if review_status:
        stmt = stmt.where(Certificate.review_status == review_status)
    if keyword:
        stmt = stmt.where(
            Certificate.cert_type.ilike(f"%{keyword}%")
            | Certificate.cert_no.ilike(f"%{keyword}%")
        )
    rows, total = await _paginate(db, stmt, params)
    items = await _decorate_certificates(db, list(rows))
    return page_of(items, total, params.page, params.size)


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
    items = await _decorate_certificates(db, list(rows))
    return page_of(items, total, params.page, params.size)


@router.get("/certificates/{certificate_id}", response_model=CertificateOut, summary="证照详情")
async def get_certificate(certificate_id: int, db: Db, _: CurrentUser):
    return await _load_certificate_out(db, certificate_id)


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
    cert = Certificate(**payload.model_dump(), review_status=REVIEW_PENDING)
    await create_and_commit(db, cert)
    return await _load_certificate_out(db, cert.id)


@router.put("/certificates/{certificate_id}", response_model=CertificateOut, summary="更新证照")
async def update_certificate(
    certificate_id: int, payload: CertificateUpdate, db: Db, _: CurrentUser
):
    cert = await get_or_404(db, Certificate, certificate_id, "证照不存在")
    data = payload.model_dump(exclude_unset=True)
    # 关键信息变更后需要重新审核（首营资料复审）
    if {"cert_no", "cert_type", "valid_from", "valid_to"} & set(data):
        cert.review_status = REVIEW_PENDING
        cert.review_remark = None
        cert.reviewed_by = None
        cert.reviewed_at = None
    await update_and_commit(db, cert, data)
    return await _load_certificate_out(db, certificate_id)


@router.post(
    "/certificates/{certificate_id}/review",
    response_model=CertificateOut,
    summary="证照审核（首营资料审批）",
)
async def review_certificate(
    certificate_id: int,
    payload: CertificateReviewIn,
    db: Db,
    current: CurrentUser,
):
    cert = await get_or_404(db, Certificate, certificate_id, "证照不存在")
    approved = payload.action == "approve"
    cert.review_status = REVIEW_APPROVED if approved else REVIEW_REJECTED
    cert.review_remark = payload.remark
    cert.reviewed_by = current.id
    cert.reviewed_at = datetime.now()
    if approved:
        # 审核通过后同步一次存储态状态，便于旧接口/报表消费
        cert.status = effective_status(cert)
    else:
        cert.status = "已驳回"
    db.add(
        AuditLog(
            user_id=current.id,
            username=current.username,
            action="approve" if approved else "reject",
            module="gsp",
            detail=f"{'通过' if approved else '驳回'}证照 #{cert.id}（{cert.cert_type}）",
        )
    )
    await db.commit()
    return await _load_certificate_out(db, certificate_id)


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


# ----------------------------- 资质档案（一户一档） -----------------------------
@router.get(
    "/qualification/{entity_type}/{entity_id}",
    response_model=QualificationOut,
    summary="主体资质档案与准入结论",
)
async def get_qualification(entity_type: str, entity_id: int, db: Db, _: CurrentUser):
    if entity_type not in ENTITY_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"未知的对象类型：{entity_type}（可选 customer/supplier/product/manufacturer）",
        )
    model = ENTITY_MODELS[entity_type]
    entity = await db.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{ENTITY_LABELS[entity_type]}不存在")
    result = await check_qualification(db, entity_type, entity_id)
    return QualificationOut(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=result.entity_name,
        has_profile=result.has_profile,
        compliant=result.compliant,
        blocking=[QualificationIssueOut(**asdict(issue)) for issue in result.blocking],
        warnings=[QualificationIssueOut(**asdict(issue)) for issue in result.warnings],
        certificates=await _decorate_certificates(db, result.certificates),
    )


# ----------------------------- 证照附件（扫描件归档） -----------------------------
@router.get(
    "/certificates/{certificate_id}/attachments",
    response_model=list[CertificateAttachmentOut],
    summary="证照附件列表",
)
async def list_certificate_attachments(
    certificate_id: int,
    db: Db,
    _: CurrentUser,
    include_history: bool = Query(False, description="是否包含换证留档的历史版本"),
):
    await get_or_404(db, Certificate, certificate_id, "证照不存在")
    stmt = select(CertificateAttachment).where(
        CertificateAttachment.certificate_id == certificate_id
    )
    if not include_history:
        stmt = stmt.where(CertificateAttachment.is_current.is_(True))
    rows = await db.scalars(
        stmt.order_by(
            CertificateAttachment.version.desc(), CertificateAttachment.id.desc()
        )
    )
    return [_attachment_out(row) for row in rows.all()]


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
    cert = await get_or_404(db, Certificate, certificate_id, "证照不存在")
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

    # 换证留档：新上传的扫描件成为当前版本，旧版本自动转为历史版本
    last_version = await db.scalar(
        select(func.max(CertificateAttachment.version)).where(
            CertificateAttachment.certificate_id == certificate_id
        )
    )
    await db.execute(
        update(CertificateAttachment)
        .where(
            CertificateAttachment.certificate_id == certificate_id,
            CertificateAttachment.is_current.is_(True),
        )
        .values(is_current=False)
    )
    attachment = CertificateAttachment(
        certificate_id=certificate_id,
        file_name=file_name,
        object_key=object_key,
        content_type=file.content_type,
        size=len(data),
        uploaded_by=current.id,
        version=(last_version or 0) + 1,
        is_current=True,
    )
    db.add(attachment)
    db.add(
        AuditLog(
            user_id=current.id,
            username=current.username,
            action="upload",
            module="gsp",
            detail=f"上传证照 #{cert.id}（{cert.cert_type}）扫描件：{file_name}",
        )
    )
    await db.commit()
    await db.refresh(attachment)
    return _attachment_out(attachment)


async def _serve_attachment(
    attachment_id: int, db: AsyncSession, current: CurrentUser, inline: bool
) -> Response:
    """从对象存储取出扫描件并回传（inline=浏览器内预览，attachment=下载）。"""
    attachment = await get_or_404(db, CertificateAttachment, attachment_id, "附件不存在")
    try:
        data = await storage.get_object(attachment.object_key)
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        raise HTTPException(status_code=503, detail=f"对象存储不可用：{exc}") from exc
    # GSP 留痕：记录查阅行为
    db.add(
        AuditLog(
            user_id=current.id,
            username=current.username,
            action="preview" if inline else "download",
            module="gsp",
            detail=f"{'预览' if inline else '下载'}证照附件 #{attachment.id}：{attachment.file_name}",
        )
    )
    await db.commit()
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type=attachment_media_type(attachment.file_name, attachment.content_type),
        headers={
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{quote(attachment.file_name)}"
            ),
            # 预览需要在浏览器内渲染，这里禁止把内容当成 HTML 执行
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/attachments/{attachment_id}/preview", summary="在线预览证照附件")
async def preview_certificate_attachment(
    attachment_id: int, db: Db, current: CurrentUser
):
    """以 inline 方式回传扫描件，浏览器可直接渲染 PDF / JPG / PNG 等。"""
    return await _serve_attachment(attachment_id, db, current, inline=True)


@router.get("/attachments/{attachment_id}/download", summary="下载证照附件")
async def download_certificate_attachment(
    attachment_id: int, db: Db, current: CurrentUser
):
    return await _serve_attachment(attachment_id, db, current, inline=False)


@router.delete("/attachments/{attachment_id}", response_model=Message, summary="删除证照附件")
async def delete_certificate_attachment(attachment_id: int, db: Db, _: CurrentUser):
    attachment = await get_or_404(db, CertificateAttachment, attachment_id, "附件不存在")
    try:
        await storage.delete_object(attachment.object_key)
    except Exception:  # 文件已丢失/存储不可用时仍清理记录
        pass
    await delete_and_commit(db, attachment)
    return Message(message="附件已删除")


# ----------------------------- 到期预警中心 -----------------------------
@router.get("/alerts", response_model=Page[GspAlertOut], summary="GSP 到期预警（证照+批次）")
async def list_alerts(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    category: str = Query("all", pattern="^(all|certificate|batch)$"),
    level: str = Query("all", pattern="^(all|已过期|30天内|60天内|90天内)$"),
    days: int = Query(90, ge=1, le=3650, description="level=all 时的预警窗口天数"),
):
    today = date.today()
    cert_where = [
        Certificate.valid_to.isnot(None),
        _alert_bucket(Certificate.valid_to, level, today, days),
    ]
    batch_where = [
        Batch.expiry_date.isnot(None),
        _alert_bucket(Batch.expiry_date, level, today, days),
    ]
    parts = []
    if category in ("all", "certificate"):
        parts.append(
            select(
                literal("certificate").label("category"),
                Certificate.id.label("ref_id"),
                Certificate.cert_type.label("title"),
                Certificate.entity_type.label("entity_type"),
                Certificate.entity_id.label("entity_id"),
                Certificate.valid_to.label("valid_to"),
            ).where(*cert_where)
        )
    if category in ("all", "batch"):
        parts.append(
            select(
                literal("batch").label("category"),
                Batch.id.label("ref_id"),
                Batch.batch_no.label("title"),
                literal("product").label("entity_type"),
                Batch.product_id.label("entity_id"),
                Batch.expiry_date.label("valid_to"),
            ).where(*batch_where)
        )
    union = parts[0].subquery() if len(parts) == 1 else union_all(*parts).subquery()
    total = (
        await db.scalar(select(func.count()).select_from(union))
    ) or 0
    rows = (
        await db.execute(
            select(union)
            .order_by(union.c.valid_to, union.c.category, union.c.ref_id)
            .offset((params.page - 1) * params.size)
            .limit(params.size)
        )
    ).all()
    names = await _entity_name_map(
        db, {(row.entity_type, row.entity_id) for row in rows}
    )
    items = [
        GspAlertOut(
            category=row.category,
            ref_id=row.ref_id,
            title=row.title,
            subject=names.get((row.entity_type, row.entity_id))
            or f"{ENTITY_LABELS.get(row.entity_type, row.entity_type)} #{row.entity_id}",
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            valid_to=row.valid_to,
            days_left=(row.valid_to - today).days,
            level=_level_of((row.valid_to - today).days),
        )
        for row in rows
    ]
    return page_of(items, total, params.page, params.size)


@router.get("/alerts/summary", response_model=GspAlertSummaryOut, summary="GSP 预警统计")
async def alert_summary(db: Db, _: CurrentUser):
    today = date.today()
    summary = GspAlertSummaryOut()

    async def count(model, column, level: str) -> int:
        return (
            await db.scalar(
                select(func.count())
                .select_from(model)
                .where(column.isnot(None), _alert_bucket(column, level, today, 90))
            )
        ) or 0

    cert_total = batch_total = 0
    for level, attr in zip(
        ("已过期", "30天内", "60天内", "90天内"),
        ("expired", "within_30", "within_60", "within_90"),
    ):
        certs = await count(Certificate, Certificate.valid_to, level)
        batches = await count(Batch, Batch.expiry_date, level)
        setattr(summary, attr, certs + batches)
        cert_total += certs
        batch_total += batches
    summary.certificate_total = cert_total
    summary.batch_total = batch_total
    summary.pending_review = (
        await db.scalar(
            select(func.count())
            .select_from(Certificate)
            .where(Certificate.review_status == REVIEW_PENDING)
        )
    ) or 0
    return summary


# ----------------------------- 批次/效期管理 -----------------------------
@router.get("/batches", response_model=Page[BatchOut], summary="批次列表")
async def list_batches(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    product_id: int | None = None,
    status: str | None = None,
    keyword: str | None = None,
):
    stmt = select(Batch).order_by(Batch.expiry_date, Batch.id)
    if product_id is not None:
        stmt = stmt.where(Batch.product_id == product_id)
    if status:
        stmt = stmt.where(Batch.status == status)
    if keyword:
        stmt = stmt.where(Batch.batch_no.ilike(f"%{keyword}%"))
    rows, total = await _paginate(db, stmt, params)
    return page_of(list(rows), total, params.page, params.size)


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
    return page_of(list(rows), total, params.page, params.size)


@router.get("/batches/{batch_id}", response_model=BatchOut, summary="批次详情")
async def get_batch(batch_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Batch, batch_id, "批次不存在")


@router.post("/batches", response_model=BatchOut, status_code=201, summary="创建批次")
async def create_batch(payload: BatchCreate, db: Db, _: CurrentUser):
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
