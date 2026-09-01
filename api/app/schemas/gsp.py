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


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    cert_type: str
    cert_no: str | None
    valid_from: date | None
    valid_to: date | None
    status: str
    remark: str | None
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
