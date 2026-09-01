from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    customer_type: str = "单体药房"
    coop_level: str = "普通客户"
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    license_no: str | None = None
    credit_limit: float = 0
    status: str = "正常"
    remark: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    customer_type: str | None = None
    coop_level: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    license_no: str | None = None
    credit_limit: float | None = None
    status: str | None = None
    remark: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    customer_type: str
    coop_level: str
    contact_person: str | None
    phone: str | None
    email: str | None
    province: str | None
    city: str | None
    address: str | None
    license_no: str | None
    credit_limit: float
    status: str
    remark: str | None
    created_at: datetime


class SupplierCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    credit_days: int = 30
    status: str = "合作中"


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    credit_days: int | None = None
    status: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    contact_person: str | None
    phone: str | None
    email: str | None
    province: str | None
    city: str | None
    address: str | None
    credit_days: int
    status: str
    created_at: datetime


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country: str | None = None
    description: str | None = None


class ManufacturerUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    description: str | None = None


class ManufacturerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str | None
    description: str | None
    created_at: datetime


class CategoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    category_id: int
    manufacturer_id: int
    supplier_id: int
    approval_no: str | None = None
    specification: str | None = None
    unit: str = "盒"
    dosage_form: str | None = None
    storage_condition: str = "常温"
    is_cold_chain: bool = False
    shelf_life_months: int = 24
    cost_price: float
    standard_price: float
    is_active: bool = True
    listed_date: date


class ProductUpdate(BaseModel):
    name: str | None = None
    category_id: int | None = None
    manufacturer_id: int | None = None
    supplier_id: int | None = None
    approval_no: str | None = None
    specification: str | None = None
    unit: str | None = None
    dosage_form: str | None = None
    storage_condition: str | None = None
    is_cold_chain: bool | None = None
    shelf_life_months: int | None = None
    cost_price: float | None = None
    standard_price: float | None = None
    is_active: bool | None = None
    listed_date: date | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category_id: int
    manufacturer_id: int
    supplier_id: int
    approval_no: str | None
    specification: str | None
    unit: str
    dosage_form: str | None
    storage_condition: str
    is_cold_chain: bool
    shelf_life_months: int
    cost_price: float
    standard_price: float
    is_active: bool
    listed_date: date
    created_at: datetime


class PriceAdjustCreate(BaseModel):
    effective_date: date
    new_price: float
    change_reason: str | None = None


class PriceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    effective_date: date
    old_price: float | None
    new_price: float
    change_reason: str | None
    created_at: datetime


class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    province: str | None = None
    city: str | None = None
    address: str | None = None
    manager_name: str | None = None
    phone: str | None = None
    has_cold_chain: bool = True
    status: str = "正常"


class WarehouseUpdate(BaseModel):
    name: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    manager_name: str | None = None
    phone: str | None = None
    has_cold_chain: bool | None = None
    status: str | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    province: str | None
    city: str | None
    address: str | None
    manager_name: str | None
    phone: str | None
    has_cold_chain: bool
    status: str
    created_at: datetime
