from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SalesReturnItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    reason: str | None = None


class SalesReturnCreate(BaseModel):
    sales_order_id: int
    return_date: date
    reason: str | None = None
    remark: str | None = None
    items: list[SalesReturnItemIn] = Field(min_length=1)


class SalesReturnItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_return_id: int
    product_id: int
    quantity: int
    unit_price: float
    amount: float
    reason: str | None


class SalesReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    return_no: str
    sales_order_id: int
    customer_id: int
    warehouse_id: int
    return_date: date
    status: str
    reason: str | None
    total_amount: float
    remark: str | None
    created_at: datetime
    items: list[SalesReturnItemOut] = []
