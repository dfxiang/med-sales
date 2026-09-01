from httpx import AsyncClient


def _sales_payload(ids: dict) -> dict:
    return {
        "customer_id": ids["customer_id"],
        "employee_id": ids["employee_id"],
        "warehouse_id": ids["warehouse_id"],
        "order_date": "2026-08-10",
        "invoice_type": "增值税专用发票",
        "settlement_method": "现款",
        "delivery_type": "常温运输",
        "items": [{"product_id": ids["product_id"], "quantity": 10, "discount_rate": 0.1}],
    }


async def test_sales_order_flow(client: AsyncClient, auth_headers: dict, ids: dict):
    # 创建（单价 15，数量 10，折扣 10% → 小计 150，优惠 15，应收 135）
    resp = await client.post(
        "/api/sales-orders", headers=auth_headers, json=_sales_payload(ids)
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["order_no"].startswith("SO20260810")
    assert order["status"] == "待付款"
    assert order["subtotal_amount"] == 150.0
    assert order["discount_amount"] == 15.0
    assert order["total_amount"] == 135.0
    assert order["cost_amount"] == 100.0
    order_id = order["id"]

    # 列表
    resp = await client.get("/api/sales-orders?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # 详情
    resp = await client.get(f"/api/sales-orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["unit_price"] == 15.0

    # 发货出库（库存 1000 → 990）
    resp = await client.post(
        f"/api/sales-orders/{order_id}/ship",
        headers=auth_headers,
        json={"delivery_date": "2026-08-11"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "已发货"
    assert resp.json()["delivery_date"] == "2026-08-11"

    resp = await client.get("/api/inventory?page=1&size=100", headers=auth_headers)
    inv = next(i for i in resp.json()["items"] if i["product_id"] == ids["product_id"])
    assert inv["quantity"] == 990

    # 收款 → 完成
    resp = await client.post(
        "/api/payments",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "payment_date": "2026-08-12",
            "amount": 135,
            "payment_method": "银行转账",
        },
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/sales-orders/{order_id}", headers=auth_headers)
    assert resp.json()["status"] == "已完成"
    assert resp.json()["paid_amount"] == 135.0


async def test_sales_order_cancel(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.post(
        "/api/sales-orders", headers=auth_headers, json=_sales_payload(ids)
    )
    order_id = resp.json()["id"]

    resp = await client.post(f"/api/sales-orders/{order_id}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "已取消"

    # 已取消订单不能发货
    resp = await client.post(
        f"/api/sales-orders/{order_id}/ship",
        headers=auth_headers,
        json={"delivery_date": "2026-08-11"},
    )
    assert resp.status_code == 400


async def test_sales_order_delete(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.post(
        "/api/sales-orders", headers=auth_headers, json=_sales_payload(ids)
    )
    order_id = resp.json()["id"]
    resp = await client.delete(f"/api/sales-orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_sales_order_frozen_customer(client: AsyncClient, auth_headers: dict, ids: dict):
    await client.put(
        f"/api/customers/{ids['customer_id']}",
        headers=auth_headers,
        json={"status": "冻结"},
    )
    resp = await client.post(
        "/api/sales-orders", headers=auth_headers, json=_sales_payload(ids)
    )
    assert resp.status_code == 400


async def test_sales_order_insufficient_stock(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = _sales_payload(ids)
    payload["items"] = [
        {"product_id": ids["product_id"], "quantity": 99999, "discount_rate": 0}
    ]
    resp = await client.post("/api/sales-orders", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    order_id = resp.json()["id"]
    resp = await client.post(
        f"/api/sales-orders/{order_id}/ship",
        headers=auth_headers,
        json={"delivery_date": "2026-08-11"},
    )
    assert resp.status_code == 400
