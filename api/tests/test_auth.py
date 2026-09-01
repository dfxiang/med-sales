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
