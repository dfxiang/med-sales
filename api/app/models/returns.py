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


class SalesReturn(Base):
    __tablename__ = "sales_return"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    return_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    sales_order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sales_order.id"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer.id"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouse.id"), nullable=False
    )
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="待处理", nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100))
    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    remark: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    items: Mapped[list["SalesReturnItem"]] = relationship(
        back_populates="sales_return", lazy="selectin", cascade="all, delete-orphan"
    )
    sales_order: Mapped["SalesOrder"] = relationship()
    customer: Mapped["Customer"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()


class SalesReturnItem(Base):
    __tablename__ = "sales_return_item"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    sales_return_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sales_return.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100))

    sales_return: Mapped[SalesReturn] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
