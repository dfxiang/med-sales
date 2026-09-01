from httpx import AsyncClient


async def test_supplier_crud(client: AsyncClient, auth_headers: dict):
    payload = {
        "code": "SUP002",
        "name": "华西药业",
        "contact_person": "赵六",
        "credit_days": 45,
        "status": "合作中",
    }
    resp = await client.post("/api/suppliers", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    sid = resp.json()["id"]

    resp = await client.get(f"/api/suppliers/{sid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "华西药业"

    resp = await client.get("/api/suppliers?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/suppliers/{sid}", headers=auth_headers, json={"status": "暂停合作"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "暂停合作"

    resp = await client.delete(f"/api/suppliers/{sid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_supplier_duplicate_code(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/suppliers",
        headers=auth_headers,
        json={"code": "SUP001", "name": "重复供应商"},
    )
    assert resp.status_code == 400
