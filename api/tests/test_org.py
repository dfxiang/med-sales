from httpx import AsyncClient


async def test_department_crud(client: AsyncClient, auth_headers: dict, ids: dict):
    resp = await client.post(
        "/api/departments",
        headers=auth_headers,
        json={"code": "D002", "name": "采购部", "description": "采购管理"},
    )
    assert resp.status_code == 201, resp.text
    dep_id = resp.json()["id"]

    resp = await client.get(f"/api/departments/{dep_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == "D002"

    resp = await client.get("/api/departments?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/departments/{dep_id}",
        headers=auth_headers,
        json={"name": "采购中心"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "采购中心"

    resp = await client.delete(f"/api/departments/{dep_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_employee_crud(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = {
        "code": "E0002",
        "name": "李四",
        "gender": "女",
        "department_id": ids["department_id"],
        "position": "采购专员",
        "hire_date": "2023-01-01",
        "employment_status": "在职",
    }
    resp = await client.post("/api/employees", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    emp_id = resp.json()["id"]

    resp = await client.get(f"/api/employees/{emp_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "李四"

    resp = await client.get(
        f"/api/employees?department_id={ids['department_id']}&page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.put(
        f"/api/employees/{emp_id}",
        headers=auth_headers,
        json={"position": "高级采购专员", "employment_status": "离职"},
    )
    assert resp.status_code == 200
    assert resp.json()["position"] == "高级采购专员"

    resp = await client.delete(f"/api/employees/{emp_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_employee_duplicate_code(client: AsyncClient, auth_headers: dict, ids: dict):
    payload = {
        "code": "E0001",
        "name": "重复工号",
        "department_id": ids["department_id"],
        "hire_date": "2023-01-01",
    }
    resp = await client.post("/api/employees", headers=auth_headers, json=payload)
    assert resp.status_code == 400
