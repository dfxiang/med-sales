from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPk


class SalesOrder(Base):
    __tablename__ = "sales_order"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer.id"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employee.id"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouse.id"), nullable=False
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="待付款", nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subtotal_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    paid_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    cost_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    shipping_address: Mapped[str | None] = mapped_column(String(300))
    invoice_type: Mapped[str] = mapped_column(
        String(30), default="增值税专用发票", nullable=False
    )
    settlement_method: Mapped[str] = mapped_column(
        String(30), default="现款", nullable=False
    )
    delivery_type: Mapped[str] = mapped_column(
        String(30), default="常温运输", nullable=False
    )
    delivery_date: Mapped[date | None] = mapped_column(Date)
    remark: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    items: Mapped[list["SalesOrderItem"]] = relationship(
        back_populates="sales_order", lazy="selectin", cascade="all, delete-orphan"
    )
    customer: Mapped["Customer"] = relationship()
    employee: Mapped["Employee"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()


class SalesOrderItem(Base):
    __tablename__ = "sales_order_item"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    sales_order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sales_order.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    discount_rate: Mapped[float] = mapped_column(
        Numeric(5, 4), default=0, nullable=False
    )
    discount_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    sales_order: Mapped[SalesOrder] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
