from httpx import AsyncClient


async def test_warehouse_crud(client: AsyncClient, auth_headers: dict):
    payload = {
        "code": "WH-002",
        "name": "广州中心仓",
        "province": "广东省",
        "city": "广州",
        "has_cold_chain": True,
        "status": "正常",
    }
    resp = await client.post("/api/warehouses", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    wid = resp.json()["id"]

    resp = await client.get(f"/api/warehouses/{wid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == "WH-002"

    resp = await client.get("/api/warehouses?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/warehouses/{wid}", headers=auth_headers, json={"manager_name": "仓库主管"}
    )
    assert resp.status_code == 200
    assert resp.json()["manager_name"] == "仓库主管"

    resp = await client.delete(f"/api/warehouses/{wid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_warehouse_duplicate_code(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/warehouses",
        headers=auth_headers,
        json={"code": "WH-001", "name": "重复仓库"},
    )
    assert resp.status_code == 400
