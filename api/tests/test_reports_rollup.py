"""汇总表（预聚合）与订单写路径的一致性回归。

覆盖四条容易出错的路径：

* 新增订单后各口径同步更新；
* 取消订单后各口径回退（报表只统计非取消订单，汇总必须跟着回退）；
* 删除待付款订单后各口径回退；
* 增量维护之后与明细表对账一致；以及有人绕过 API 改库时对账能发现。
"""

from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.master import Customer
from app.models.sales import SalesOrder, SalesOrderItem
from app.services.rollup import check_consistency


async def _create_order(
    client: AsyncClient, auth_headers: dict, ids: dict, day: date, qty: int
) -> dict:
    resp = await client.post(
        "/api/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": ids["customer_id"],
            "employee_id": ids["employee_id"],
            "warehouse_id": ids["warehouse_id"],
            "order_date": day.isoformat(),
            "items": [{"product_id": ids["product_id"], "quantity": qty}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _summary(client: AsyncClient, auth_headers: dict, path: str) -> dict:
    resp = await client.get(path, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_rollup_tracks_create_and_cancel(
    client: AsyncClient, auth_headers: dict, ids: dict, db_engine
) -> None:
    """新增 -> 取消：商品 / 客户 / 销售员 / 日 / 看板口径全部跟着走。"""
    today = date.today()
    await _create_order(client, auth_headers, ids, today, 10)
    await _create_order(client, auth_headers, ids, today, 5)

    product = (await _summary(client, auth_headers, "/api/reports/product-summary"))[
        "items"
    ][0]
    assert product["sold_quantity"] == 15
    assert product["sales_amount"] == 225.0
    assert product["order_count"] == 2

    customer = (await _summary(client, auth_headers, "/api/reports/customer-summary"))[
        "items"
    ][0]
    assert customer["order_count"] == 2
    assert customer["total_amount"] == 225.0
    assert customer["last_order_date"] == today.isoformat()

    employee = (await _summary(client, auth_headers, "/api/reports/employee-summary"))[
        "items"
    ][0]
    assert employee["order_count"] == 2
    assert employee["total_amount"] == 225.0
    assert employee["customer_count"] == 1

    daily = (await _summary(client, auth_headers, "/api/reports/sales-daily"))["items"]
    assert [(row["sale_date"], row["order_count"]) for row in daily] == [
        (today.isoformat(), 2)
    ]

    board = await _summary(client, auth_headers, "/api/reports/dashboard")
    assert board["today_order_count"] == 2
    assert board["today_sales_amount"] == 225.0
    assert board["month_order_count"] == 2

    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        assert await check_consistency(session) == []

    # 取消其中一张订单：金额回退，且不再计入订单数
    order_id = await _order_id_of(client, auth_headers, ids, today, 10)
    resp = await client.post(f"/api/sales-orders/{order_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    product = (await _summary(client, auth_headers, "/api/reports/product-summary"))[
        "items"
    ][0]
    assert product["sold_quantity"] == 5
    assert product["order_count"] == 1

    customer = (await _summary(client, auth_headers, "/api/reports/customer-summary"))[
        "items"
    ][0]
    assert customer["order_count"] == 1
    assert customer["total_amount"] == 75.0

    board = await _summary(client, auth_headers, "/api/reports/dashboard")
    assert board["today_order_count"] == 1
    assert board["today_sales_amount"] == 75.0

    async with session_factory() as session:
        assert await check_consistency(session) == []


async def _order_id_of(
    client: AsyncClient, auth_headers: dict, ids: dict, day: date, qty: int
) -> int:
    """按客户 + 日期 + 数量定位订单（测试数据量小，直接翻列表足够）。"""
    resp = await client.get(
        f"/api/sales-orders?customer_id={ids['customer_id']}&start_date={day.isoformat()}"
        f"&end_date={day.isoformat()}",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        if item["total_quantity"] == qty:
            return item["id"]
    raise AssertionError(f"未找到数量为 {qty} 的订单")


async def test_rollup_reverts_after_delete(
    client: AsyncClient, auth_headers: dict, ids: dict, db_engine
) -> None:
    """删除待付款订单后汇总必须回退（订单已不存在，不能靠重算旧值）。"""
    today = date.today()
    order = await _create_order(client, auth_headers, ids, today, 7)

    resp = await client.delete(f"/api/sales-orders/{order['id']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    product = (await _summary(client, auth_headers, "/api/reports/product-summary"))[
        "items"
    ][0]
    assert product["sold_quantity"] == 0
    assert product["sales_amount"] == 0.0
    assert product["order_count"] == 0

    assert (await _summary(client, auth_headers, "/api/reports/sales-daily"))[
        "items"
    ] == []

    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        assert await check_consistency(session) == []


async def test_rollup_by_date_and_employee_customer_pairs(
    client: AsyncClient, auth_headers: dict, ids: dict, db_engine
) -> None:
    """多日期互不串扰；销售员的成交客户数是去重计数。"""
    today = date.today()
    yesterday = today - timedelta(days=1)

    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        second = Customer(code="C00002", name="第二测试医院")
        session.add(second)
        await session.commit()
        second_id = second.id

    await _create_order(client, auth_headers, ids, yesterday, 4)
    await _create_order(client, auth_headers, ids, today, 6)
    resp = await client.post(
        "/api/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": second_id,
            "employee_id": ids["employee_id"],
            "warehouse_id": ids["warehouse_id"],
            "order_date": today.isoformat(),
            "items": [{"product_id": ids["product_id"], "quantity": 2}],
        },
    )
    assert resp.status_code == 201, resp.text

    daily = (await _summary(client, auth_headers, "/api/reports/sales-daily"))["items"]
    assert [(row["sale_date"], row["order_count"]) for row in daily] == [
        (today.isoformat(), 2),
        (yesterday.isoformat(), 1),
    ]

    # 商品汇总是全区间口径：4 + 6 + 2 = 12
    resp = await client.get(
        "/api/reports/product-summary?page=1&size=20", headers=auth_headers
    )
    assert resp.json()["items"][0]["sold_quantity"] == 12

    employee = (await _summary(client, auth_headers, "/api/reports/employee-summary"))[
        "items"
    ][0]
    assert employee["order_count"] == 3
    assert employee["customer_count"] == 2

    board = await _summary(client, auth_headers, "/api/reports/dashboard")
    assert board["today_order_count"] == 2
    # 看板当月口径只看当月：月初第一天跑测试时，昨天属于上个月
    assert board["month_order_count"] == (3 if yesterday.month == today.month else 2)

    async with session_factory() as session:
        assert await check_consistency(session) == []


async def test_consistency_check_detects_manual_write(
    client: AsyncClient, auth_headers: dict, ids: dict, db_engine
) -> None:
    """绕过 API 直接写库（批量导入 / 手工修数）时，对账必须能发现。"""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    today = date.today()
    async with session_factory() as session:
        order = SalesOrder(
            order_no="SO-MANUAL-0001",
            customer_id=ids["customer_id"],
            employee_id=ids["employee_id"],
            warehouse_id=ids["warehouse_id"],
            order_date=today,
            status="已完成",
            item_count=1,
            total_quantity=3,
            total_amount=45,
            cost_amount=30,
        )
        session.add(order)
        await session.flush()
        session.add(
            SalesOrderItem(
                sales_order_id=order.id,
                product_id=ids["product_id"],
                quantity=3,
                unit_price=15,
                unit_cost=10,
                amount=45,
            )
        )
        await session.commit()

        issues = await check_consistency(session)
    assert issues, "手工写入明细后，汇总表与明细表应当被判定为不一致"
    assert any("sales_rollup_day" in issue for issue in issues)
