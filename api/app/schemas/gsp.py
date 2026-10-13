from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CertificateCreate(BaseModel):
    entity_type: str = Field(min_length=1, max_length=20)
    entity_id: int
    cert_type: str = Field(min_length=1, max_length=50)
    cert_no: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str = "有效"
    remark: str | None = None


class CertificateUpdate(BaseModel):
    cert_type: str | None = None
    cert_no: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str | None = None
    remark: str | None = None


class CertificateReviewIn(BaseModel):
    """首营资料审核动作。"""

    action: str = Field(pattern="^(approve|reject)$", description="approve=通过，reject=驳回")
    remark: str | None = Field(default=None, max_length=200, description="审核意见/驳回原因")


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    entity_name: str | None = None
    cert_type: str
    cert_no: str | None
    valid_from: date | None
    valid_to: date | None
    status: str
    remark: str | None
    review_status: str = "待审核"
    reviewed_by: int | None = None
    review_remark: str | None = None
    reviewed_at: datetime | None = None
    effective_status: str = "有效"
    days_to_expiry: int | None = None
    attachment_count: int = 0
    created_at: datetime


class QualificationIssueOut(BaseModel):
    cert_id: int | None
    cert_type: str
    kind: str
    detail: str


class QualificationOut(BaseModel):
    """主体资质档案 + 准入结论。"""

    entity_type: str
    entity_id: int
    entity_name: str | None
    has_profile: bool
    compliant: bool
    blocking: list[QualificationIssueOut]
    warnings: list[QualificationIssueOut]
    certificates: list[CertificateOut]


class GspAlertOut(BaseModel):
    """统一预警条目（证照到期 / 批次近效期）。"""

    category: str  # certificate / batch
    ref_id: int
    title: str
    subject: str
    entity_type: str | None = None
    entity_id: int | None = None
    valid_to: date | None = None
    days_left: int
    level: str  # 已过期 / 30天内 / 60天内 / 90天内


class GspAlertSummaryOut(BaseModel):
    expired: int = 0
    within_30: int = 0
    within_60: int = 0
    within_90: int = 0
    pending_review: int = 0
    certificate_total: int = 0
    batch_total: int = 0


class CertificateAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    certificate_id: int
    file_name: str
    content_type: str | None
    size: int
    uploaded_by: int | None
    version: int = 1
    is_current: bool = True
    # 预览相关：kind=pdf/image/other，previewable 表示浏览器能否原生渲染
    kind: str = "other"
    media_type: str = "application/octet-stream"
    previewable: bool = False
    created_at: datetime


class BatchCreate(BaseModel):
    product_id: int
    batch_no: str = Field(min_length=1, max_length=50)
    production_date: date | None = None
    expiry_date: date | None = None
    quantity: int = 0
    status: str = "正常"
    remark: str | None = None


class BatchUpdate(BaseModel):
    production_date: date | None = None
    expiry_date: date | None = None
    quantity: int | None = None
    status: str | None = None
    remark: str | None = None


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    batch_no: str
    production_date: date | None
    expiry_date: date | None
    quantity: int
    status: str
    remark: str | None
    created_at: datetime
