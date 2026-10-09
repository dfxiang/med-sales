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
