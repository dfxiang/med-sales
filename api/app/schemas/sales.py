from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.master import ProductOut


class SalesOrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    discount_rate: float = Field(default=0, ge=0, le=1)


class SalesOrderCreate(BaseModel):
    customer_id: int
    employee_id: int
    warehouse_id: int
    order_date: date
    shipping_address: str | None = None
    invoice_type: str = "增值税专用发票"
    settlement_method: str = "现款"
    delivery_type: str = "常温运输"
    delivery_date: date | None = None
    remark: str | None = None
    items: list[SalesOrderItemIn] = Field(min_length=1)


class SalesOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_order_id: int
    product_id: int
    quantity: int
    unit_price: float
    unit_cost: float
    discount_rate: float
    discount_amount: float
    amount: float
    product: ProductOut | None = None


class SalesOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    customer_id: int
    employee_id: int
    warehouse_id: int
    order_date: date
    status: str
    item_count: int
    total_quantity: int
    subtotal_amount: float
    discount_amount: float
    total_amount: float
    paid_amount: float
    cost_amount: float
    shipping_address: str | None
    invoice_type: str
    settlement_method: str
    delivery_type: str
    delivery_date: date | None
    remark: str | None
    created_at: datetime
    items: list[SalesOrderItemOut] = []


class ShipRequest(BaseModel):
    delivery_date: date
