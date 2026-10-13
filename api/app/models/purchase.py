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


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("supplier.id"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouse.id"), nullable=False
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date)
    received_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="待收货", nullable=False)
    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2), default=0, nullable=False
    )
    delivery_type: Mapped[str] = mapped_column(
        String(30), default="常温运输", nullable=False
    )
    remark: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", lazy="selectin", cascade="all, delete-orphan"
    )
    supplier: Mapped["Supplier"] = relationship()
    warehouse: Mapped["Warehouse"] = relationship()


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_item"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("purchase_order.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    received_date: Mapped[date | None] = mapped_column(Date)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
