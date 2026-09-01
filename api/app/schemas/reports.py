from datetime import date

from pydantic import BaseModel


class SalesDailyRow(BaseModel):
    sale_date: date
    order_count: int
    item_count: int
    quantity: int
    total_amount: float
    discount_amount: float
    cost_amount: float
    profit_amount: float


class SalesMonthlyRow(BaseModel):
    month: str
    order_count: int
    item_count: int
    quantity: int
    total_amount: float
    discount_amount: float
    cost_amount: float
    profit_amount: float
    prev_month_amount: float | None
    amount_growth_rate: float | None


class CustomerSummaryRow(BaseModel):
    customer_id: int
    customer_code: str
    customer_name: str
    customer_type: str
    coop_level: str
    province: str | None
    city: str | None
    phone: str | None
    order_count: int
    total_amount: float
    cost_amount: float
    profit_amount: float
    last_order_date: date | None


class EmployeeSummaryRow(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_name: str | None
    position: str | None
    order_count: int
    total_amount: float
    cost_amount: float
    profit_amount: float
    customer_count: int


class ProductSummaryRow(BaseModel):
    product_id: int
    sku: str
    product_name: str
    category_name: str | None
    manufacturer_name: str | None
    cost_price: float
    standard_price: float
    sold_quantity: int
    sales_amount: float
    gross_profit: float
    order_count: int


class OrderDetailRow(BaseModel):
    order_id: int
    order_no: str
    order_date: date
    order_status: str
    customer_id: int
    customer_name: str
    customer_type: str
    coop_level: str
    employee_id: int
    employee_name: str
    department_name: str | None
    warehouse_name: str
    product_id: int
    sku: str
    product_name: str
    category_name: str | None
    manufacturer_name: str | None
    quantity: int
    unit_price: float
    discount_amount: float
    line_amount: float
    order_amount: float
    paid_amount: float


class DashboardOut(BaseModel):
    today_order_count: int
    today_sales_amount: float
    today_profit: float
    month_order_count: int
    month_sales_amount: float
    month_profit: float
    low_stock_count: int
    pending_return_count: int
    total_receivable: float
