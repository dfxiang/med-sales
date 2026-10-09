from datetime import date, timedelta

from httpx import AsyncClient


async def test_certificate_crud(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = {
        "entity_type": "customer",
        "entity_id": ids["customer_id"],
        "cert_type": "药品经营许可证",
        "cert_no": "沪A-2026-0001",
        "valid_from": "2026-01-01",
        "valid_to": "2029-01-01",
    }
    resp = await client.post("/api/gsp/certificates", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    cid = resp.json()["id"]

    resp = await client.get(f"/api/gsp/certificates/{cid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["cert_no"] == "沪A-2026-0001"

    resp = await client.get(
        f"/api/gsp/certificates?entity_type=customer&page=1&size=10", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await client.put(
        f"/api/gsp/certificates/{cid}", headers=auth_headers, json={"status": "即将到期"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "即将到期"

    resp = await client.delete(f"/api/gsp/certificates/{cid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_certificate_expiring(client: AsyncClient, auth_headers: dict, ids: dict):
    near = (date.today() + timedelta(days=30)).isoformat()
    await client.post(
        "/api/gsp/certificates",
        headers=auth_headers,
        json={
            "entity_type": "supplier",
            "entity_id": ids["supplier_id"],
            "cert_type": "营业执照",
            "valid_to": near,
        },
    )
    resp = await client.get("/api/gsp/certificates/expiring?days=90", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


async def test_batch_crud(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = {
        "product_id": ids["product_id"],
        "batch_no": "B20260801",
        "production_date": "2026-08-01",
        "expiry_date": "2028-08-01",
        "quantity": 1000,
        "status": "正常",
    }
    resp = await client.post("/api/gsp/batches", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    bid = resp.json()["id"]

    resp = await client.get(f"/api/gsp/batches/{bid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["batch_no"] == "B20260801"

    resp = await client.get(
        f"/api/gsp/batches?product_id={ids['product_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await client.put(
        f"/api/gsp/batches/{bid}", headers=auth_headers, json={"quantity": 800}
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 800

    resp = await client.delete(f"/api/gsp/batches/{bid}", headers=auth_headers)
    assert resp.status_code == 200


async def test_batch_expiring(client: AsyncClient, auth_headers: dict, ids: dict):
    await client.post(
        "/api/gsp/batches",
        headers=auth_headers,
        json={
            "product_id": ids["product_id"],
            "batch_no": "B-OLD-001",
            "expiry_date": "2026-12-31",
            "quantity": 100,
        },
    )
    resp = await client.get("/api/gsp/batches/expiring?days=180", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1
