from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
    product_id: int
    quantity: int
    safety_stock: int
    updated_at: datetime
    warehouse_name: str | None = None
    product_name: str | None = None
    sku: str | None = None
    stock_status: str | None = None
    stock_value: float | None = None


class InventoryMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
    product_id: int
    movement_type: str
    quantity: int
    movement_date: date
    ref_table: str | None
    ref_id: int | None
    created_by: int | None
    remark: str | None
    created_at: datetime


class OpenStockItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OpenStockRequest(BaseModel):
    warehouse_id: int
    movement_date: date
    items: list[OpenStockItem] = Field(min_length=1)
