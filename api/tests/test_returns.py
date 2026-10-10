from httpx import AsyncClient


async def _create_sales_order(client, auth_headers, ids: dict) -> int:
    resp = await client.post(
        "/api/sales-orders",
        headers=auth_headers,
        json={
            "customer_id": ids["customer_id"],
            "employee_id": ids["employee_id"],
            "warehouse_id": ids["warehouse_id"],
            "order_date": "2026-08-20",
            "items": [{"product_id": ids["product_id"], "quantity": 20}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_return_flow(client: AsyncClient, auth_headers: dict, ids: dict):
    order_id = await _create_sales_order(client, auth_headers, ids)

    resp = await client.post(
        "/api/sales-returns",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "return_date": "2026-08-25",
            "reason": "质量问题",
            "items": [
                {"product_id": ids["product_id"], "quantity": 5, "unit_price": 15, "reason": "质量问题"}
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    ret = resp.json()
    assert ret["return_no"].startswith("RT20260825")
    assert ret["status"] == "待处理"
    assert ret["total_amount"] == 75.0
    assert ret["customer_name"] == "测试医院"
    assert ret["order_no"].startswith("SO")
    return_id = ret["id"]

    resp = await client.get(f"/api/sales-returns/{return_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["customer_id"] == ids["customer_id"]
    assert resp.json()["customer_name"] == "测试医院"

    resp = await client.get(
        f"/api/sales-returns?customer_id={ids['customer_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert resp.json()["items"][0]["customer_name"] == "测试医院"
    assert resp.json()["items"][0]["order_no"].startswith("SO")

    resp = await client.get("/api/sales-returns?customer_id=99999", headers=auth_headers)
    assert resp.json()["total"] == 0

    # 处理 → 退货入库
    resp = await client.post(f"/api/sales-returns/{return_id}/process", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "已完成"

    resp = await client.get("/api/inventory?page=1&size=100", headers=auth_headers)
    inv = next(i for i in resp.json()["items"] if i["product_id"] == ids["product_id"])
    assert inv["quantity"] == 1005

    # 重复处理报错
    resp = await client.post(f"/api/sales-returns/{return_id}/process", headers=auth_headers)
    assert resp.status_code == 400


async def test_return_delete(client: AsyncClient, auth_headers: dict, ids: dict):
    order_id = await _create_sales_order(client, auth_headers, ids)
    resp = await client.post(
        "/api/sales-returns",
        headers=auth_headers,
        json={
            "sales_order_id": order_id,
            "return_date": "2026-08-26",
            "items": [
                {"product_id": ids["product_id"], "quantity": 1, "unit_price": 15}
            ],
        },
    )
    return_id = resp.json()["id"]
    resp = await client.delete(f"/api/sales-returns/{return_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_return_missing_order(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/sales-returns",
        headers=auth_headers,
        json={
            "sales_order_id": 99999,
            "return_date": "2026-08-26",
            "items": [{"product_id": 1, "quantity": 1, "unit_price": 15}],
        },
    )
    assert resp.status_code == 404
