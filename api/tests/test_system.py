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


async def test_user_profile_fields(client: AsyncClient, auth_headers: dict):
    """显示名称 / 电话 / 邮箱：建号可填、可回读、可更新。"""
    resp = await client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "username": "profile01",
            "password": "pass1234",
            "display_name": "  王小明  ",
            "phone": "138-0000-1234",
            "email": "wangxm@example.com",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    user_id = body["id"]
    assert body["display_name"] == "王小明"  # 自动去空格
    assert body["phone"] == "138-0000-1234"
    assert body["email"] == "wangxm@example.com"
    assert body["avatar_url"] == "/api/avatars/default.png"

    # 省略显示名称时默认取用户名
    resp = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "profile02", "password": "pass1234"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["display_name"] == "profile02"

    # 更新资料
    resp = await client.put(
        f"/api/users/{user_id}",
        headers=auth_headers,
        json={"display_name": "王小明-改", "phone": "", "email": "new@example.com"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "王小明-改"
    assert resp.json()["phone"] is None  # 空串 = 清空
    assert resp.json()["email"] == "new@example.com"

    # 显示名称必填：不允许置空
    resp = await client.put(
        f"/api/users/{user_id}", headers=auth_headers, json={"display_name": ""}
    )
    assert resp.status_code == 400
    assert "显示名称不能为空" in resp.json()["detail"]

    # 非法邮箱被拒
    resp = await client.put(
        f"/api/users/{user_id}", headers=auth_headers, json={"email": "not-an-email"}
    )
    assert resp.status_code == 422

    # 关键词可按显示名称命中
    resp = await client.get("/api/users?keyword=王小明", headers=auth_headers)
    assert resp.status_code == 200
    assert [item["username"] for item in resp.json()["items"]] == ["profile01"]


async def test_admin_reset_password(client: AsyncClient, auth_headers: dict):
    """管理员重置密码：不需要原密码、不需要二次确认，且必须留审计。"""
    created = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "reset01", "password": "pass1234"},
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    # 新密码过短 → 422
    resp = await client.post(
        f"/api/users/{user_id}/reset-password",
        headers=auth_headers,
        json={"new_password": "123"},
    )
    assert resp.status_code == 422

    # 只传 new_password 即可重置（没有原密码 / 确认密码字段）
    resp = await client.post(
        f"/api/users/{user_id}/reset-password",
        headers=auth_headers,
        json={"new_password": "brandnew123"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "密码已重置"

    # 旧密码失效、新密码可登录
    old = await client.post(
        "/api/auth/login", json={"username": "reset01", "password": "pass1234"}
    )
    assert old.status_code == 401
    new = await client.post(
        "/api/auth/login", json={"username": "reset01", "password": "brandnew123"}
    )
    assert new.status_code == 200

    # 审计日志：独立 action，且不含密码明文
    logs = await client.get("/api/audit-logs?module=system&page=1&size=50", headers=auth_headers)
    assert logs.status_code == 200
    entries = [item for item in logs.json()["items"] if item["action"] == "reset_password"]
    assert entries and "reset01" in entries[0]["detail"]
    assert all("brandnew123" not in (item["detail"] or "") for item in logs.json()["items"])


async def test_reset_password_requires_permission(client: AsyncClient, auth_headers: dict):
    """无 system:user:manage 的账号不能重置他人密码（越权回归点）。"""
    created = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": "plain01", "password": "pass1234"},
    )
    victim_id = created.json()["id"]
    plain_id = (
        await client.post(
            "/api/users",
            headers=auth_headers,
            json={"username": "plain02", "password": "pass1234"},
        )
    ).json()["id"]

    login = await client.post(
        "/api/auth/login", json={"username": "plain02", "password": "pass1234"}
    )
    plain_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.post(
        f"/api/users/{victim_id}/reset-password",
        headers=plain_headers,
        json={"new_password": "brandnew123"},
    )
    assert resp.status_code == 403

    # 顺带确认：无权限账号连用户列表都看不到
    assert (await client.get("/api/users", headers=plain_headers)).status_code == 403
    assert plain_id != victim_id
