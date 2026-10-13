"""候选数据接口（`/api/options/*`）：只吐主键 / 编码 / 名称，登录即可访问。

这组接口存在的意义就是「把下拉候选与管理页列表分开」，因此这里重点守住三条：
字段集合不扩大、无业务权限也能读、管理页接口的权限判定不受影响。
"""

from httpx import AsyncClient

ENTITIES = (
    "customer",
    "product",
    "category",
    "manufacturer",
    "supplier",
    "warehouse",
    "employee",
    "department",
)


async def test_requires_login(client: AsyncClient):
    assert (await client.get("/api/options/customer")).status_code == 401


async def test_payload_is_only_id_code_name(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/options/product", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert items, "预置商品应当出现在候选里"
    # 关键约束：候选接口不得带出成本价、挂网价等业务字段
    assert set(items[0]) == {"id", "code", "name"}
    assert items[0]["code"] == "SKU-TEST-001"
    assert items[0]["name"] == "测试药品"


async def test_all_entities_available_without_business_permission(
    client: AsyncClient, auth_headers: dict
):
    """无任何业务权限的账号：管理页接口 403，候选接口照常可用。"""
    username = "options_probe"
    created = await client.post(
        "/api/users",
        headers=auth_headers,
        json={"username": username, "password": "probe1234", "display_name": "候选探测"},
    )
    assert created.status_code == 201, created.text

    login = await client.post(
        "/api/auth/login", json={"username": username, "password": "probe1234"}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert (await client.get("/api/products", headers=headers)).status_code == 403
    assert (await client.get("/api/customers", headers=headers)).status_code == 403

    for entity in ENTITIES:
        resp = await client.get(f"/api/options/{entity}", headers=headers)
        assert resp.status_code == 200, f"{entity}: {resp.text}"
        assert resp.json(), f"{entity} 应当返回预置数据"


async def test_keyword_filter_and_single_lookup(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/options/customer", headers=auth_headers, params={"keyword": "测试"}
    )
    items = resp.json()
    assert [item["name"] for item in items] == ["测试医院"]

    # 编码片段也能命中
    by_code = (
        await client.get(
            "/api/options/customer", headers=auth_headers, params={"keyword": "C00001"}
        )
    ).json()
    assert [item["id"] for item in by_code] == [items[0]["id"]]

    single = await client.get(f"/api/options/customer/{items[0]['id']}", headers=auth_headers)
    assert single.status_code == 200
    assert single.json() == items[0]


async def test_manufacturer_without_code_field(client: AsyncClient, auth_headers: dict):
    items = (await client.get("/api/options/manufacturer", headers=auth_headers)).json()
    assert items
    assert items[0]["code"] is None


async def test_unknown_entity_and_missing_id(client: AsyncClient, auth_headers: dict):
    assert (await client.get("/api/options/nope", headers=auth_headers)).status_code == 404
    resp = await client.get("/api/options/customer/999999", headers=auth_headers)
    assert resp.status_code == 404
    assert "不存在" in resp.json()["detail"]
