from httpx import AsyncClient


def _purchase_payload(ids: dict) -> dict:
    return {
        "supplier_id": ids["supplier_id"],
        "warehouse_id": ids["warehouse_id"],
        "order_date": "2026-08-01",
        "expected_date": "2026-08-05",
        "delivery_type": "常温运输",
        "items": [{"product_id": ids["product_id"], "quantity": 100, "unit_cost": 9.5}],
    }


async def test_purchase_order_flow(client: AsyncClient, auth_headers: dict, ids: dict):
    # 创建
    resp = await client.post(
        "/api/purchase-orders", headers=auth_headers, json=_purchase_payload(ids)
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["order_no"].startswith("PO20260801")
    assert order["status"] == "待收货"
    assert order["total_amount"] == 950.0
    item_id = order["items"][0]["id"]

    # 列表
    resp = await client.get("/api/purchase-orders?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # 详情
    resp = await client.get(f"/api/purchase-orders/{order['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["quantity"] == 100

    # 部分收货
    resp = await client.post(
        f"/api/purchase-orders/{order['id']}/receive",
        headers=auth_headers,
        json={
            "received_date": "2026-08-05",
            "items": [{"item_id": item_id, "received_quantity": 40}],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "部分收货"

    # 收齐
    resp = await client.post(
        f"/api/purchase-orders/{order['id']}/receive",
        headers=auth_headers,
        json={
            "received_date": "2026-08-06",
            "items": [{"item_id": item_id, "received_quantity": 60}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "已完成"

    # 库存应增加 100
    resp = await client.get("/api/inventory?page=1&size=100", headers=auth_headers)
    items = resp.json()["items"]
    inv = next(i for i in items if i["product_id"] == ids["product_id"])
    assert inv["quantity"] == 1100

    # 超量收货应报错
    new_order = await client.post(
        "/api/purchase-orders", headers=auth_headers, json=_purchase_payload(ids)
    )
    new_item_id = new_order.json()["items"][0]["id"]
    resp = await client.post(
        f"/api/purchase-orders/{new_order.json()['id']}/receive",
        headers=auth_headers,
        json={
            "received_date": "2026-08-07",
            "items": [{"item_id": new_item_id, "received_quantity": 999}],
        },
    )
    assert resp.status_code == 400


async def test_purchase_order_update_and_delete(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.post(
        "/api/purchase-orders", headers=auth_headers, json=_purchase_payload(ids)
    )
    order_id = resp.json()["id"]

    payload = _purchase_payload(ids)
    payload["remark"] = "更新备注"
    resp = await client.put(
        f"/api/purchase-orders/{order_id}", headers=auth_headers, json=payload
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["remark"] == "更新备注"

    resp = await client.delete(f"/api/purchase-orders/{order_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_purchase_order_missing_supplier(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = _purchase_payload(ids)
    payload["supplier_id"] = 99999
    resp = await client.post("/api/purchase-orders", headers=auth_headers, json=payload)
    assert resp.status_code == 404
