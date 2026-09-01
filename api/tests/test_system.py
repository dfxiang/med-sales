from httpx import AsyncClient


async def test_user_crud_and_role_bind(client: AsyncClient, auth_headers: dict):
    # 创建
    resp = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "saler01", "password": "pass1234", "is_active": True},
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]
    assert resp.json()["username"] == "saler01"

    # 重复创建
    resp = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "saler01", "password": "pass1234"},
    )
    assert resp.status_code == 400

    # 列表
    resp = await client.get("/api/users?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    # 详情
    resp = await client.get(f"/api/users/{user_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "saler01"

    # 更新
    resp = await client.put(
        f"/api/users/{user_id}",
        headers=auth_headers,
        json={"password": "newpass123", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # 分配角色
    role = await client.post(
        "/api/roles", headers=auth_headers, json={"name": "销售员", "description": "销售"}
    )
    assert role.status_code == 201, role.text
    role_id = role.json()["id"]
    resp = await client.post(
        f"/api/users/{user_id}/roles",
        headers=auth_headers,
        json={"role_ids": [role_id]},
    )
    assert resp.status_code == 200
    assert resp.json()["roles"][0]["name"] == "销售员"

    # 删除
    resp = await client.delete(f"/api/users/{user_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_role_crud_and_permission_bind(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/roles", headers=auth_headers, json={"name": "采购员", "description": "采购"}
    )
    assert resp.status_code == 201, resp.text
    role_id = resp.json()["id"]

    resp = await client.get(f"/api/roles/{role_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.put(
        f"/api/roles/{role_id}", headers=auth_headers, json={"name": "高级采购员"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "高级采购员"

    perm = await client.post(
        "/api/permissions",
        headers=auth_headers,
        json={"code": "purchase:create", "name": "创建采购单"},
    )
    assert perm.status_code == 201, perm.text

    resp = await client.post(
        f"/api/roles/{role_id}/permissions",
        headers=auth_headers,
        json={"permission_ids": [perm.json()["id"]]},
    )
    assert resp.status_code == 200
    assert resp.json()["permissions"][0]["code"] == "purchase:create"

    resp = await client.delete(f"/api/roles/{role_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_permission_crud(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/permissions",
        headers=auth_headers,
        json={"code": "report:view", "name": "查看报表"},
    )
    assert resp.status_code == 201, resp.text
    perm_id = resp.json()["id"]

    resp = await client.get(f"/api/permissions/{perm_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.put(
        f"/api/permissions/{perm_id}", headers=auth_headers, json={"name": "查看全部报表"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "查看全部报表"

    resp = await client.get("/api/permissions?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    resp = await client.delete(f"/api/permissions/{perm_id}", headers=auth_headers)
    assert resp.status_code == 200


async def test_roles_list_and_audit_logs(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/roles?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await client.get("/api/audit-logs?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    resp = await client.get("/api/audit-logs?username=admin", headers=auth_headers)
    assert resp.status_code == 200


async def test_missing_user_404(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/users/99999", headers=auth_headers)
    assert resp.status_code == 404
