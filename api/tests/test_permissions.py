"""权限控制：接口级校验、通配权限、内置项保护与关键字过滤。"""

from httpx import AsyncClient


async def _create_user(client: AsyncClient, auth_headers: dict, username: str) -> int:
    resp = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": username, "password": "pass1234"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _login(client: AsyncClient, username: str, password: str = "pass1234") -> dict:
    resp = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _grant(client: AsyncClient, auth_headers: dict, user_id: int, codes: list[str]) -> int:
    """建一个只含指定权限编码的角色并分配给用户，返回角色 id。"""
    resp = await client.get("/api/permissions", headers=auth_headers, params={"size": 200})
    catalog = {p["code"]: p["id"] for p in resp.json()["items"]}
    permission_ids = []
    for code in codes:
        if code in catalog:
            permission_ids.append(catalog[code])
            continue
        created = await client.post(
            "/api/permissions", headers=auth_headers, json={"code": code, "name": code}
        )
        assert created.status_code == 201, created.text
        permission_ids.append(created.json()["id"])
    role = await client.post(
        "/api/roles",
        headers=auth_headers,
        json={"name": f"临时角色-{'-'.join(codes)}", "description": "测试用"},
    )
    assert role.status_code == 201, role.text
    role_id = role.json()["id"]
    resp = await client.post(
        f"/api/roles/{role_id}/permissions",
        headers=auth_headers,
        json={"permission_ids": permission_ids},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/api/users/{user_id}/roles", headers=auth_headers, json={"role_ids": [role_id]}
    )
    assert resp.status_code == 200, resp.text
    return role_id


async def test_me_exposes_permission_codes(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["permissions"] == ["all"]
    assert body["is_superuser"] is True
    assert body["roles"][0]["name"] == "管理员"


async def test_user_without_permission_is_blocked(client: AsyncClient, auth_headers: dict):
    await _create_user(client, auth_headers, "no_perm_user")
    headers = await _login(client, "no_perm_user")

    for method, path in (
        ("get", "/api/users"),
        ("get", "/api/roles"),
        ("get", "/api/permissions"),
        ("get", "/api/audit-logs"),
        ("get", "/api/customers"),
        ("get", "/api/reports/dashboard"),
    ):
        resp = await getattr(client, method)(path, headers=headers)
        assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}"
        assert "权限不足" in resp.json()["detail"]

    resp = await client.post(
        "/api/users",
        headers=headers,
        json={"username": "hacker", "password": "pass1234"},
    )
    assert resp.status_code == 403

    # 登录态本身有效，能读到自己的信息
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["permissions"] == []
    assert resp.json()["is_superuser"] is False


async def test_view_permission_allows_read_only(client: AsyncClient, auth_headers: dict):
    user_id = await _create_user(client, auth_headers, "user_viewer")
    await _grant(client, auth_headers, user_id, ["system:user:view"])
    headers = await _login(client, "user_viewer")

    resp = await client.get("/api/users", headers=headers)
    assert resp.status_code == 200, resp.text

    # 只有查看权限时不允许维护
    resp = await client.post(
        "/api/users", headers=headers, json={"username": "hacker", "password": "pass1234"}
    )
    assert resp.status_code == 403
    resp = await client.get("/api/roles", headers=headers)
    assert resp.status_code == 403


async def test_all_permission_is_wildcard(client: AsyncClient, auth_headers: dict):
    user_id = await _create_user(client, auth_headers, "user_super")
    await _grant(client, auth_headers, user_id, ["all"])
    headers = await _login(client, "user_super")

    for path in ("/api/users", "/api/roles", "/api/gsp/certificates", "/api/receivables"):
        resp = await client.get(path, headers=headers)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.json()["is_superuser"] is True


async def test_cannot_delete_or_disable_self(client: AsyncClient, auth_headers: dict, ids: dict):
    admin_id = ids["admin_id"]
    resp = await client.delete(f"/api/users/{admin_id}", headers=auth_headers)
    assert resp.status_code == 400
    assert "当前登录账号" in resp.json()["detail"]

    resp = await client.put(
        f"/api/users/{admin_id}", headers=auth_headers, json={"is_active": False}
    )
    assert resp.status_code == 400


async def test_cannot_strip_own_admin_role(client: AsyncClient, auth_headers: dict, ids: dict):
    """唯一管理员给自己摘掉特权角色时会被拒绝，避免系统失去可用管理员。"""
    resp = await client.post(
        f"/api/users/{ids['admin_id']}/roles", headers=auth_headers, json={"role_ids": []}
    )
    assert resp.status_code == 400
    assert "至少一个可用的管理员账号" in resp.json()["detail"]


async def test_builtin_all_permission_is_protected(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/permissions", headers=auth_headers, params={"size": 200})
    all_perm = next(p for p in resp.json()["items"] if p["code"] == "all")

    resp = await client.delete(f"/api/permissions/{all_perm['id']}", headers=auth_headers)
    assert resp.status_code == 400
    assert "不允许删除" in resp.json()["detail"]

    # 管理员角色的 all 权限不允许被摘掉，避免把自己锁死
    roles = await client.get("/api/roles", headers=auth_headers)
    admin_role = next(r for r in roles.json()["items"] if r["name"] == "管理员")
    resp = await client.post(
        f"/api/roles/{admin_role['id']}/permissions",
        headers=auth_headers,
        json={"permission_ids": []},
    )
    assert resp.status_code == 400
    assert "不允许从角色上移除" in resp.json()["detail"]


async def test_permission_in_use_cannot_be_deleted(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/permissions",
        headers=auth_headers,
        json={"code": "temp:view", "name": "临时权限"},
    )
    permission_id = resp.json()["id"]
    role = await client.post(
        "/api/roles", headers=auth_headers, json={"name": "临时角色A", "description": "测试"}
    )
    role_id = role.json()["id"]
    await client.post(
        f"/api/roles/{role_id}/permissions",
        headers=auth_headers,
        json={"permission_ids": [permission_id]},
    )

    resp = await client.delete(f"/api/permissions/{permission_id}", headers=auth_headers)
    assert resp.status_code == 400
    assert "解除关联" in resp.json()["detail"]


async def test_role_in_use_cannot_be_deleted(client: AsyncClient, auth_headers: dict):
    user_id = await _create_user(client, auth_headers, "role_bound_user")
    role_id = await _grant(client, auth_headers, user_id, ["system:user:view"])

    resp = await client.delete(f"/api/roles/{role_id}", headers=auth_headers)
    assert resp.status_code == 400
    assert "解除关联" in resp.json()["detail"]


async def test_keyword_filters_and_audit_trail(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/api/roles", headers=auth_headers, json={"name": "关键字角色", "description": "过滤验证"}
    )
    resp = await client.get("/api/roles", headers=auth_headers, params={"keyword": "关键字"})
    assert resp.status_code == 200
    assert [r["name"] for r in resp.json()["items"]] == ["关键字角色"]

    resp = await client.get("/api/permissions", headers=auth_headers, params={"keyword": "sales:"})
    assert resp.status_code == 200
    # 测试库未跑启动同步，允许为空；有数据时必须命中编码
    assert all("sales:" in p["code"] for p in resp.json()["items"])

    logs = await client.get(
        "/api/audit-logs", headers=auth_headers, params={"module": "system", "size": 50}
    )
    assert logs.status_code == 200
    assert any("创建角色 关键字角色" in (row["detail"] or "") for row in logs.json()["items"])
