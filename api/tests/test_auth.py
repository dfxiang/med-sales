from httpx import AsyncClient


async def test_login_success(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    assert resp.status_code == 401


async def test_me(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "admin"
    assert body["is_active"] is True


async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token(client: AsyncClient):
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer bad-token"})
    assert resp.status_code == 401


async def test_get_token_by_api_key(client: AsyncClient, ids: dict):
    resp = await client.post(
        "/api/auth/token",
        json={"api_key": "test-api-key-1", "user_id": ids["admin_id"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    # 拿到的令牌和登录一样，可正常访问受保护接口
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


async def test_get_token_with_second_key(client: AsyncClient, ids: dict):
    """轮换期配置多个 key，任意一个都可用。"""
    resp = await client.post(
        "/api/auth/token",
        json={"api_key": "test-api-key-2", "user_id": ids["admin_id"]},
    )
    assert resp.status_code == 200, resp.text


async def test_get_token_wrong_key(client: AsyncClient, ids: dict):
    resp = await client.post(
        "/api/auth/token",
        json={"api_key": "wrong-key", "user_id": ids["admin_id"]},
    )
    assert resp.status_code == 401


async def test_get_token_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/token",
        json={"api_key": "test-api-key-1", "user_id": 99999},
    )
    assert resp.status_code == 401


async def test_update_me_profile(client: AsyncClient, auth_headers: dict):
    """自助改资料：除用户名外的资料字段都可以改。"""
    resp = await client.put(
        "/api/auth/me",
        headers=auth_headers,
        json={
            "display_name": "系统管理员",
            "phone": "13900001234",
            "email": "admin@example.com",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["display_name"] == "系统管理员"
    assert body["phone"] == "13900001234"
    assert body["email"] == "admin@example.com"
    assert body["username"] == "admin"  # 用户名不变

    # GET /auth/me 能回读
    me = await client.get("/api/auth/me", headers=auth_headers)
    assert me.json()["display_name"] == "系统管理员"

    # 电话 / 邮箱可清空
    resp = await client.put(
        "/api/auth/me", headers=auth_headers, json={"phone": "", "email": ""}
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] is None
    assert resp.json()["email"] is None

    # 显示名称必填：不允许清空
    resp = await client.put("/api/auth/me", headers=auth_headers, json={"display_name": ""})
    assert resp.status_code == 400
    assert "显示名称不能为空" in resp.json()["detail"]

    # 非法邮箱
    resp = await client.put(
        "/api/auth/me", headers=auth_headers, json={"email": "bad-email"}
    )
    assert resp.status_code == 422

    # 未带令牌
    assert (await client.put("/api/auth/me", json={"display_name": "x"})).status_code == 401


async def test_update_me_profile_has_audit_log(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/auth/me", headers=auth_headers, json={"phone": "13900009999"}
    )
    assert resp.status_code == 200
    logs = await client.get("/api/audit-logs?module=auth&page=1&size=50", headers=auth_headers)
    details = [item["detail"] or "" for item in logs.json()["items"]]
    assert any("更新个人资料" in detail and "电话" in detail for detail in details)


async def test_update_me_profile_without_user_manage_permission(
    client: AsyncClient, auth_headers: dict
):
    """关键回归点：普通账号（无 system:user:manage）也能维护自己的资料。"""
    created = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "self01", "password": "pass1234"},
    )
    assert created.status_code == 201, created.text
    login = await client.post(
        "/api/auth/login", json={"username": "self01", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.put(
        "/api/auth/me", headers=headers, json={"display_name": "自助改名"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "自助改名"
    # 越权字段不会产生副作用：用户名与启用状态不受影响
    assert resp.json()["username"] == "self01"
    assert resp.json()["is_active"] is True


async def test_change_my_password(client: AsyncClient, auth_headers: dict):
    """自助改密：校验原密码 + 两次新密码一致 + 审计，旧密码失效。"""
    created = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "pw01", "password": "pass1234"},
    )
    assert created.status_code == 201, created.text
    login = await client.post(
        "/api/auth/login", json={"username": "pw01", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 两次新密码不一致
    resp = await client.put(
        "/api/auth/me/password",
        headers=headers,
        json={
            "old_password": "pass1234",
            "new_password": "newpass1234",
            "confirm_password": "newpass4321",
        },
    )
    assert resp.status_code == 400
    assert "两次输入的新密码不一致" in resp.json()["detail"]

    # 原密码错误
    resp = await client.put(
        "/api/auth/me/password",
        headers=headers,
        json={
            "old_password": "wrong-pass",
            "new_password": "newpass1234",
            "confirm_password": "newpass1234",
        },
    )
    assert resp.status_code == 400
    assert "原密码不正确" in resp.json()["detail"]

    # 新密码与原密码相同
    resp = await client.put(
        "/api/auth/me/password",
        headers=headers,
        json={
            "old_password": "pass1234",
            "new_password": "pass1234",
            "confirm_password": "pass1234",
        },
    )
    assert resp.status_code == 400
    assert "不能与原密码相同" in resp.json()["detail"]

    # 长度不足
    resp = await client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"old_password": "pass1234", "new_password": "123", "confirm_password": "123"},
    )
    assert resp.status_code == 422

    # 正常修改
    resp = await client.put(
        "/api/auth/me/password",
        headers=headers,
        json={
            "old_password": "pass1234",
            "new_password": "newpass1234",
            "confirm_password": "newpass1234",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "密码已修改"

    # 旧密码失效、新密码可登录
    old = await client.post(
        "/api/auth/login", json={"username": "pw01", "password": "pass1234"}
    )
    assert old.status_code == 401
    new = await client.post(
        "/api/auth/login", json={"username": "pw01", "password": "newpass1234"}
    )
    assert new.status_code == 200

    # 审计日志：记录事件但不含密码明文
    logs = await client.get("/api/audit-logs?module=auth&page=1&size=50", headers=auth_headers)
    items = logs.json()["items"]
    assert any((item["detail"] or "") == "修改登录密码" for item in items)
    assert all("newpass1234" not in (item["detail"] or "") for item in items)


async def test_change_my_password_requires_auth(client: AsyncClient):
    resp = await client.put(
        "/api/auth/me/password",
        json={
            "old_password": "admin123",
            "new_password": "newpass1234",
            "confirm_password": "newpass1234",
        },
    )
    assert resp.status_code == 401
