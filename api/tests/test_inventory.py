from httpx import AsyncClient


async def test_inventory_list_and_detail(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.get(
        f"/api/inventory?warehouse_id={ids['warehouse_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] >= 1
    item = resp.json()["items"][0]
    assert item["stock_status"] in ("库存不足", "库存预警", "库存充足")
    assert item["stock_value"] == item["quantity"] * 10

    resp = await client.get(f"/api/inventory/{item['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["product_name"] == "测试药品"

    # 状态过滤
    resp = await client.get("/api/inventory?status=库存充足&page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200


async def test_open_stock(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.post(
        "/api/inventory/open-stock",
        headers=auth_headers,
        json={
            "warehouse_id": ids["warehouse_id"],
            "movement_date": "2026-08-01",
            "items": [{"product_id": ids["product_id"], "quantity": 500}],
        },
    )
    assert resp.status_code == 201, resp.text

    resp = await client.get("/api/inventory?page=1&size=100", headers=auth_headers)
    inv = next(i for i in resp.json()["items"] if i["product_id"] == ids["product_id"])
    assert inv["quantity"] == 1500


async def test_inventory_movements(client: AsyncClient, auth_headers: dict, ids: dict):
    # 先做一期初入库产生流水
    await client.post(
        "/api/inventory/open-stock",
        headers=auth_headers,
        json={
            "warehouse_id": ids["warehouse_id"],
            "movement_date": "2026-08-01",
            "items": [{"product_id": ids["product_id"], "quantity": 10}],
        },
    )
    resp = await client.get(
        f"/api/inventory/movements?product_id={ids['product_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] >= 1
    movement = resp.json()["items"][0]
    assert movement["movement_type"] == "期初入库"
    assert movement["quantity"] == 10

    resp = await client.get(f"/api/inventory/movements/{movement['id']}", headers=auth_headers)
    assert resp.status_code == 200


async def test_movement_missing_404(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/inventory/movements/99999", headers=auth_headers)
    assert resp.status_code == 404
