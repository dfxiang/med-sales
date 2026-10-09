"""GSP 合规领域服务：首营资质档案与交易准入校验。

业务闭环：
    主体建档 -> 录入证照（+ 扫描件归档）-> 质量员审核 -> 形成有效资质档案
    -> 交易前准入校验 -> 到期预警 -> 换证归档（新版本扫描件，旧版留档）

本模块只依赖 ORM 模型，供各业务路由（销售/采购）与 GSP 路由共用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.master import (
    Certificate,
    Customer,
    Manufacturer,
    Product,
    Supplier,
)
from app.models.system import AuditLog, User

# 证照主体类型 -> 模型
ENTITY_MODELS: dict[str, type] = {
    "customer": Customer,
    "supplier": Supplier,
    "product": Product,
    "manufacturer": Manufacturer,
}

ENTITY_LABELS: dict[str, str] = {
    "customer": "客户",
    "supplier": "供应商",
    "product": "商品",
    "manufacturer": "生产厂家",
}

# 审核状态流转
REVIEW_PENDING = "待审核"
REVIEW_APPROVED = "已通过"
REVIEW_REJECTED = "已驳回"
REVIEW_STATUSES = (REVIEW_PENDING, REVIEW_APPROVED, REVIEW_REJECTED)


def effective_status(cert: Certificate, today: date | None = None) -> str:
    """证照的综合状态：审核状态优先，其次按有效期计算。"""
    today = today or date.today()
    if cert.review_status == REVIEW_REJECTED:
        return "已驳回"
    if cert.review_status == REVIEW_PENDING:
        return "待审核"
    if cert.valid_to is not None:
        if cert.valid_to < today:
            return "已过期"
        if cert.valid_to <= today + timedelta(days=settings.gsp_expiry_warning_days):
            return "即将到期"
    if cert.valid_from is not None and cert.valid_from > today:
        return "未生效"
    return "有效"


def days_to_expiry(cert: Certificate, today: date | None = None) -> int | None:
    if cert.valid_to is None:
        return None
    today = today or date.today()
    return (cert.valid_to - today).days


async def entity_name(db: AsyncSession, entity_type: str, entity_id: int) -> str | None:
    model = ENTITY_MODELS.get(entity_type)
    if model is None:
        return None
    obj = await db.get(model, entity_id)
    if obj is None:
        return None
    return getattr(obj, "name", None) or getattr(obj, "sku", None)


@dataclass
class QualificationIssue:
    """一条资质问题记录。"""

    cert_id: int | None
    cert_type: str
    kind: str  # 已驳回 / 待审核 / 已过期 / 未生效 / 无资质档案
    detail: str


@dataclass
class QualificationResult:
    """某个主体的资质档案校验结果。"""

    entity_type: str
    entity_id: int
    entity_name: str | None
    certificates: list[Certificate] = field(default_factory=list)
    blocking: list[QualificationIssue] = field(default_factory=list)
    warnings: list[QualificationIssue] = field(default_factory=list)

    @property
    def has_profile(self) -> bool:
        """是否已建立首营资质档案（录入了任意证照）。"""
        return bool(self.certificates)

    @property
    def compliant(self) -> bool:
        return not self.blocking


async def check_qualification(
    db: AsyncSession, entity_type: str, entity_id: int, today: date | None = None
) -> QualificationResult:
    """汇总主体的资质档案并给出准入结论（不抛异常）。"""
    today = today or date.today()
    certs = list(
        (
            await db.scalars(
                select(Certificate)
                .where(
                    Certificate.entity_type == entity_type,
                    Certificate.entity_id == entity_id,
                )
                .order_by(Certificate.id)
            )
        ).all()
    )
    result = QualificationResult(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=await entity_name(db, entity_type, entity_id),
        certificates=certs,
    )

    if not certs:
        if settings.gsp_strict_qualification:
            result.blocking.append(
                QualificationIssue(
                    cert_id=None,
                    cert_type="-",
                    kind="无资质档案",
                    detail=f"该{ENTITY_LABELS.get(entity_type, entity_type)}尚未建立首营资质档案",
                )
            )
        return result

    label = ENTITY_LABELS.get(entity_type, entity_type)
    who = result.entity_name or entity_id
    for cert in certs:
        status = effective_status(cert, today)
        if status == "已驳回":
            suffix = f"（{cert.review_remark}）" if cert.review_remark else ""
            result.blocking.append(
                QualificationIssue(
                    cert.id,
                    cert.cert_type,
                    status,
                    f"{label}「{who}」的{cert.cert_type}审核未通过{suffix}",
                )
            )
        elif status == "待审核":
            result.blocking.append(
                QualificationIssue(
                    cert.id,
                    cert.cert_type,
                    status,
                    f"{label}「{who}」的{cert.cert_type}尚未审核通过",
                )
            )
        elif status in ("已过期", "未生效"):
            result.blocking.append(
                QualificationIssue(
                    cert.id,
                    cert.cert_type,
                    status,
                    f"{label}「{who}」的{cert.cert_type}有效期异常"
                    f"（{cert.valid_from or '-'} ~ {cert.valid_to or '-'}）",
                )
            )
        elif status == "即将到期":
            result.warnings.append(
                QualificationIssue(
                    cert.id,
                    cert.cert_type,
                    status,
                    f"{label}「{who}」的{cert.cert_type}将于 {cert.valid_to} 到期"
                    f"（剩余 {days_to_expiry(cert, today)} 天）",
                )
            )
    return result


async def assert_qualification(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action_label: str,
    current: User | None = None,
) -> QualificationResult:
    """交易准入校验：资质不合规时抛出 400。"""
    result = await check_qualification(db, entity_type, entity_id)
    if settings.gsp_enforce_qualification and result.blocking:
        detail = "；".join(issue.detail for issue in result.blocking)
        await _log_block(db, current, action_label, detail)
        raise HTTPException(
            status_code=400,
            detail=f"GSP 资质校验未通过，不能{action_label}：{detail}",
        )
    return result


async def assert_qualifications(
    db: AsyncSession,
    targets: list[tuple[str, int]],
    action_label: str,
    current: User | None = None,
) -> None:
    """批量校验多个主体（如订单中的多个商品），合并报错信息。"""
    if not settings.gsp_enforce_qualification:
        return
    problems: list[str] = []
    seen: set[tuple[str, int]] = set()
    for entity_type, entity_id in targets:
        key = (entity_type, entity_id)
        if key in seen:
            continue
        seen.add(key)
        result = await check_qualification(db, entity_type, entity_id)
        problems.extend(issue.detail for issue in result.blocking)
    if problems:
        detail = "；".join(problems)
        await _log_block(db, current, action_label, detail)
        raise HTTPException(
            status_code=400,
            detail=f"GSP 资质校验未通过，不能{action_label}：{detail}",
        )


async def _log_block(
    db: AsyncSession, current: User | None, action_label: str, detail: str
) -> None:
    """被拦截的交易写入审计日志，满足 GSP 留痕要求。"""
    if current is None:
        return
    db.add(
        AuditLog(
            user_id=current.id,
            username=current.username,
            action="block",
            module="gsp",
            detail=f"拦截{action_label}：{detail}"[:500],
        )
    )
    await db.commit()
