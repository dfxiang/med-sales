from httpx import AsyncClient


async def _create_order(client, auth_headers, ids: dict) -> int:
    resp = await client.post(
        "/api/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": ids["customer_id"],
            "employee_id": ids["employee_id"],
            "warehouse_id": ids["warehouse_id"],
            "order_date": "2026-08-01",
            "settlement_method": "月结30天",
            "items": [{"product_id": ids["product_id"], "quantity": 10}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_payment_crud(client: AsyncClient, auth_headers: dict, ids: dict):
    order_id = await _create_order(client, auth_headers, ids)

    resp = await client.post(
        "/api/payments",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "payment_date": "2026-08-05",
            "amount": 100,
            "payment_method": "银行转账",
        },
    )
    assert resp.status_code == 201, resp.text
    payment_id = resp.json()["id"]
    assert resp.json()["remark"] is not None

    resp = await client.get(f"/api/payments/{payment_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["amount"] == 100.0
    assert resp.json()["customer_name"] == "测试医院"
    assert resp.json()["order_no"].startswith("SO")

    resp = await client.get(
        f"/api/payments?customer_id={ids['customer_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # 订单已收金额更新
    resp = await client.get(f"/api/sales-orders/{order_id}", headers=auth_headers)
    assert resp.json()["paid_amount"] == 100.0

    # 超收报错（订单应收 150）
    resp = await client.post(
        "/api/payments",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "payment_date": "2026-08-06",
            "amount": 100,
            "payment_method": "现金",
        },
    )
    assert resp.status_code == 400

    resp = await client.delete(f"/api/payments/{payment_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_payment_full_settlement(client: AsyncClient, auth_headers: dict, ids: dict):
    order_id = await _create_order(client, auth_headers, ids)
    resp = await client.post(
        "/api/payments",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "payment_date": "2026-08-05",
            "amount": 150,
            "payment_method": "对公转账",
        },
    )
    assert resp.status_code == 201, resp.text
    resp = await client.get(f"/api/sales-orders/{order_id}", headers=auth_headers)
    assert resp.json()["status"] == "已完成"


async def test_receivables(client: AsyncClient, auth_headers: dict, ids: dict):
    await _create_order(client, auth_headers, ids)
    resp = await client.get("/api/receivables", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1
    row = resp.json()["items"][0]
    assert row["receivable"] == 150.0
    assert row["customer_name"] == "测试医院"

    resp = await client.get(
        f"/api/receivables?customer_id={ids['customer_id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # 结算方式过滤（订单为月结30天）
    resp = await client.get(
        "/api/receivables?settlement_method=月结30天", headers=auth_headers
    )
    assert resp.json()["total"] == 1
    resp = await client.get("/api/receivables?settlement_method=现款", headers=auth_headers)
    assert resp.json()["total"] == 0

    # 只看逾期：下单日期 2026-08-01 已过期，且非现款结算
    resp = await client.get("/api/receivables?overdue_only=true", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["days_overdue"] > 0
    resp = await client.get("/api/receivables?overdue_only=true&as_of=2026-08-01", headers=auth_headers)
    assert resp.json()["total"] == 0


async def test_payment_missing_order(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/payments",
        headers=auth_headers,
        json={
            "sales_order_id": 99999,
            "payment_date": "2026-08-05",
            "amount": 10,
            "payment_method": "现金",
        },
    )
    assert resp.status_code == 404


async def test_payment_list_customer_name_and_filters(
    client: AsyncClient, auth_headers: dict, ids: dict
):
    order_id = await _create_order(client, auth_headers, ids)
    resp = await client.post(
        "/api/payments",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "payment_date": "2026-08-05",
            "amount": 100,
            "payment_method": "银行转账",
        },
    )
    assert resp.status_code == 201, resp.text

    # 列表直接返回客户名称（前端不再按主键反查）
    resp = await client.get(
        f"/api/payments?customer_id={ids['customer_id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["customer_name"] == "测试医院"

    # 客户名称模糊查询（收款页客户输入框直接输入名称时走这条路径）
    resp = await client.get("/api/payments?customer_name=测试&page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    resp = await client.get("/api/payments?customer_name=不存在的客户", headers=auth_headers)
    assert resp.json()["total"] == 0

    # 付款日期范围
    resp = await client.get(
        "/api/payments?start_date=2026-08-01&end_date=2026-08-05", headers=auth_headers
    )
    assert resp.json()["total"] == 1
    resp = await client.get(
        "/api/payments?start_date=2026-09-01&end_date=2026-09-30", headers=auth_headers
    )
    assert resp.json()["total"] == 0

    # 订单号模糊查询 / 订单 ID 过滤
    order_no = item["order_no"]
    assert order_no
    resp = await client.get(
        f"/api/payments?order_no={order_no[-6:]}&page=1&size=10", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    resp = await client.get("/api/payments?order_no=SO_NOT_EXIST", headers=auth_headers)
    assert resp.json()["total"] == 0

    resp = await client.get(
        f"/api/payments?sales_order_id={order_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert {row["sales_order_id"] for row in resp.json()["items"]} == {order_id}
    resp = await client.get("/api/payments?sales_order_id=99999", headers=auth_headers)
    assert resp.json()["total"] == 0
