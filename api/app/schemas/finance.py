from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    sales_order_id: int
    payment_date: date
    amount: float = Field(gt=0)
    payment_method: str
    status: str = "成功"
    remark: str | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_order_id: int
    order_no: str | None = None
    customer_id: int
    customer_name: str | None = None
    payment_date: date
    amount: float
    payment_method: str
    status: str
    remark: str | None
    created_at: datetime


class ReceivableRow(BaseModel):
    customer_id: int
    customer_name: str
    order_id: int
    order_no: str
    order_date: date
    total_amount: float
    paid_amount: float
    receivable: float
    settlement_method: str
    days_overdue: int
