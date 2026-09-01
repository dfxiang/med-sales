from httpx import AsyncClient


async def test_category_crud(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/categories",
        headers=auth_headers,
        json={"code": "CAT-TCM", "name": "中成药", "sort_order": 4},
    )
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]

    resp = await client.get(f"/api/categories/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "中成药"

    resp = await client.get("/api/categories?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/categories/{cid}", headers=auth_headers, json={"sort_order": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 1

    resp = await client.delete(f"/api/categories/{cid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_manufacturer_crud(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/manufacturers",
        headers=auth_headers,
        json={"name": "康泰制药", "country": "中国"},
    )
    assert resp.status_code == 201, resp.text
    mid = resp.json()["id"]

    resp = await client.get(f"/api/manufacturers/{mid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "康泰制药"

    resp = await client.get("/api/manufacturers?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/manufacturers/{mid}", headers=auth_headers, json={"country": "美国"}
    )
    assert resp.status_code == 200
    assert resp.json()["country"] == "美国"

    resp = await client.delete(f"/api/manufacturers/{mid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_product_crud_and_price(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = {
        "sku": "SKU-TEST-002",
        "name": "测试器械",
        "category_id": ids["category_id"],
        "manufacturer_id": ids["manufacturer_id"],
        "supplier_id": ids["supplier_id"],
        "specification": "1套/箱",
        "unit": "套",
        "cost_price": 500,
        "standard_price": 800,
        "listed_date": "2023-01-01",
    }
    resp = await client.post("/api/products", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    pid = resp.json()["id"]

    resp = await client.get(f"/api/products/{pid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["sku"] == "SKU-TEST-002"

    resp = await client.get(
        f"/api/products?category_id={ids['category_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/products/{pid}", headers=auth_headers, json={"standard_price": 850}
    )
    assert resp.status_code == 200
    assert resp.json()["standard_price"] == 850.0

    # 价格调整
    resp = await client.post(
        f"/api/products/{pid}/prices",
        headers=auth_headers,
        json={"effective_date": "2024-01-01", "new_price": 900, "change_reason": "挂网价调整"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["old_price"] == 850.0
    assert resp.json()["new_price"] == 900.0

    # 价格历史
    resp = await client.get(f"/api/products/{pid}/prices?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await client.delete(f"/api/products/{pid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_product_duplicate_sku(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = {
        "sku": "SKU-TEST-001",
        "name": "重复商品",
        "category_id": ids["category_id"],
        "manufacturer_id": ids["manufacturer_id"],
        "supplier_id": ids["supplier_id"],
        "cost_price": 1,
        "standard_price": 2,
        "listed_date": "2023-01-01",
    }
    resp = await client.post("/api/products", headers=auth_headers, json=payload)
    assert resp.status_code == 400
