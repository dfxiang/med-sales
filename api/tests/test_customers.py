from httpx import AsyncClient


async def test_customer_crud(client: AsyncClient, auth_headers: dict):
    payload = {
        "code": "C00002",
        "name": "华东药房连锁",
        "customer_type": "连锁药房",
        "coop_level": "重点客户",
        "contact_person": "王五",
        "province": "上海市",
        "city": "上海",
        "credit_limit": 50000,
        "status": "正常",
    }
    resp = await client.post("/api/customers", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]

    resp = await client.get(f"/api/customers/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "华东药房连锁"

    resp = await client.get(
        "/api/customers?customer_type=连锁药房&page=1&size=10", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await client.put(
        f"/api/customers/{cid}",
        headers=auth_headers,
        json={"coop_level": "战略合作", "credit_limit": 200000},
    )
    assert resp.status_code == 200
    assert resp.json()["coop_level"] == "战略合作"

    resp = await client.delete(f"/api/customers/{cid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_customer_duplicate_code(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.post(
        "/api/customers",
        headers=auth_headers,
        json={"code": "C00001", "name": "重复客户"},
    )
    assert resp.status_code == 400


async def test_customer_missing_404(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/customers/99999", headers=auth_headers)
    assert resp.status_code == 404
