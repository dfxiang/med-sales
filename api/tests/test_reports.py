from datetime import date, timedelta

from httpx import AsyncClient


async def _seed_orders(client: AsyncClient, auth_headers: dict, ids: dict) -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    for d, qty in [(today, 10), (today, 5), (today, 7)]:
        resp = await client.post(
            "/api/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": ids["customer_id"],
                "employee_id": ids["employee_id"],
                "warehouse_id": ids["warehouse_id"],
                "order_date": d.isoformat(),
                "items": [{"product_id": ids["product_id"], "quantity": qty}],
            },
        )
        assert resp.status_code == 201, resp.text


async def test_reports_all(client: AsyncClient, auth_headers: dict, ids: dict):
    await _seed_orders(client, auth_headers, ids)
    today = date.today()
    today_str = today.isoformat()

    resp = await client.get("/api/reports/sales-daily", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    daily = resp.json()["items"]
    assert len(daily) == 1
    day1 = next(d for d in daily if d["sale_date"] == today_str)
    assert day1["order_count"] == 3
    assert day1["total_amount"] == 330.0
    assert day1["profit_amount"] == 110.0

    resp = await client.get(
        f"/api/reports/sales-daily?start_date={today_str}&end_date={today_str}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

    resp = await client.get("/api/reports/sales-monthly", headers=auth_headers)
    assert resp.status_code == 200
    monthly = resp.json()["items"]
    assert monthly[0]["month"] == today.strftime("%Y-%m-01")
    assert monthly[0]["total_amount"] == 330.0
    assert monthly[0]["order_count"] == 3

    resp = await client.get("/api/reports/customer-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["order_count"] == 3
    assert resp.json()["items"][0]["total_amount"] == 330.0

    resp = await client.get("/api/reports/employee-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["order_count"] == 3
    assert resp.json()["items"][0]["customer_count"] == 1

    resp = await client.get("/api/reports/product-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["sold_quantity"] == 22
    assert resp.json()["items"][0]["sales_amount"] == 330.0

    resp = await client.get("/api/reports/order-detail?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    row = resp.json()["items"][0]
    assert row["customer_name"] == "测试医院"
    assert row["product_name"] == "测试药品"

    resp = await client.get(
        "/api/reports/order-detail?customer_id=%d&page=1&size=10" % ids["customer_id"],
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/api/reports/inventory-status", headers=auth_headers)
    assert resp.status_code == 200
    assert any(i["product_name"] == "测试药品" for i in resp.json()["items"])

    resp = await client.get("/api/reports/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["today_order_count"] == 3
    assert body["today_sales_amount"] == 330.0
    assert body["month_order_count"] == 3
    assert body["month_sales_amount"] == 330.0
