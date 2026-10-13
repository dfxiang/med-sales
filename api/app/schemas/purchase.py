from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.master import ProductOut


class PurchaseOrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: float = Field(gt=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    order_date: date
    expected_date: date | None = None
    delivery_type: str = "常温运输"
    remark: str | None = None
    items: list[PurchaseOrderItemIn] = Field(min_length=1)


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_id: int
    product_id: int
    quantity: int
    unit_cost: float
    amount: float
    received_quantity: int
    received_date: date | None
    product: ProductOut | None = None


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    supplier_id: int
    supplier_name: str | None = None
    warehouse_id: int
    warehouse_name: str | None = None
    order_date: date
    expected_date: date | None
    received_date: date | None
    status: str
    total_amount: float
    delivery_type: str
    remark: str | None
    created_at: datetime
    items: list[PurchaseOrderItemOut] = []


class ReceiveItemIn(BaseModel):
    item_id: int
    received_quantity: int = Field(gt=0)


class PurchaseReceiveIn(BaseModel):
    received_date: date
    items: list[ReceiveItemIn] = Field(min_length=1)
