"""销售报表汇总表（预聚合的派生数据）。

为什么需要这些表
----------------
报表要按商品 / 客户 / 销售员 / 日期聚合 160 万行销售明细，每次请求重算一遍是
秒级开销（实测 0.15~0.69s），且单进程 uvicorn 下并发请求会串行排队。
这些表把「每次请求全量重算」变成「读一张几百到几十万行的小表」。

设计约束（改动前请先读 docs/销售报表汇总表.md）
--------------------------------------------
* ``sales_order`` / ``sales_order_item`` 是**唯一事实来源**，本模块所有表都是
  可随时重建的派生数据；
* 维护方式是**按键重算**：某张订单新增 / 取消 / 删除后，只重算它涉及到的
  日期、商品、客户、销售员这几个键，不做全表重建；
* 重算是幂等的：先按主键删除命中行，再从明细表重新聚合插入。因此任何写路径
  漏掉、或有人手工改库，都可以用 ``scripts/rebuild_sales_rollup.py`` 重新对齐；
* 只统计 ``sales_order.status != '已取消'`` 的订单，与报表口径一致（取消订单必须
  从汇总里回退，这正是"重算"而不是"累加"的原因）。
"""

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

MONEY = Numeric(18, 2)


class SalesRollupDay(Base):
    """按业务日期汇总（日 / 月报表、经营看板的当日与当月口径）。"""

    __tablename__ = "sales_rollup_day"

    order_date: Mapped[date] = mapped_column(Date, primary_key=True)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    discount_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    cost_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)


class SalesRollupProduct(Base):
    """按商品汇总（商品销售汇总报表）。

    注意：这里只存从明细聚合出来的数量 / 金额 / 订单数，**不存毛利**。
    报表的毛利口径是「销售额 - 销售数量 × 商品当前成本价」，依赖
    ``product.cost_price`` 的实时值，无法预先固化在汇总表里。
    """

    __tablename__ = "sales_rollup_product"

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product.id", ondelete="CASCADE"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sales_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SalesRollupCustomer(Base):
    """按客户汇总（客户销售汇总报表）。"""

    __tablename__ = "sales_rollup_customer"

    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer.id", ondelete="CASCADE"), primary_key=True
    )
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    cost_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    last_order_date: Mapped[date | None] = mapped_column(Date)


class SalesRollupEmployee(Base):
    """按销售员汇总（销售员业绩汇总报表的金额 / 单数口径）。"""

    __tablename__ = "sales_rollup_employee"

    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True
    )
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    cost_amount: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)


class SalesRollupEmployeeCustomer(Base):
    """销售员 × 客户 的有序对（销售员业绩里的「成交客户数」= 去重计数）。

    去重计数无法用「金额求和」这类可累加字段表示，所以单独存一层对表：
    每个销售员有多少客户，就是这张表里它名下的行数。
    """

    __tablename__ = "sales_rollup_employee_customer"

    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer.id", ondelete="CASCADE"), primary_key=True
    )
