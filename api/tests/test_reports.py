from datetime import date, timedelta

from httpx import AsyncClient


async def _seed_orders(client: AsyncClient, auth_headers: dict, ids: dict) -> None:
    today = date.today()
    yesterday = today - timedelta(days=1)
    for d, qty in [(today, 10), (today, 5), (today, 7)]:
        resp = await client.post(
            "/api/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": ids["customer_id"],
                "employee_id": ids["employee_id"],
                "warehouse_id": ids["warehouse_id"],
                "order_date": d.isoformat(),
                "items": [{"product_id": ids["product_id"], "quantity": qty}],
            },
        )
        assert resp.status_code == 201, resp.text


async def test_reports_all(client: AsyncClient, auth_headers: dict, ids: dict):
    await _seed_orders(client, auth_headers, ids)
    today = date.today()
    today_str = today.isoformat()

    resp = await client.get("/api/reports/sales-daily", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    daily = resp.json()["items"]
    assert len(daily) == 1
    day1 = next(d for d in daily if d["sale_date"] == today_str)
    assert day1["order_count"] == 3
    assert day1["total_amount"] == 330.0
    assert day1["profit_amount"] == 110.0

    resp = await client.get(
        f"/api/reports/sales-daily?start_date={today_str}&end_date={today_str}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1

    resp = await client.get("/api/reports/sales-monthly", headers=auth_headers)
    assert resp.status_code == 200
    monthly = resp.json()["items"]
    assert monthly[0]["month"] == today.strftime("%Y-%m-01")
    assert monthly[0]["total_amount"] == 330.0
    assert monthly[0]["order_count"] == 3

    resp = await client.get("/api/reports/customer-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["order_count"] == 3
    assert resp.json()["items"][0]["total_amount"] == 330.0

    # 按客户过滤（客户选择控件的查询条件）
    resp = await client.get(
        f"/api/reports/customer-summary?customer_id={ids['customer_id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["customer_name"] == "测试医院"
    resp = await client.get(
        "/api/reports/customer-summary?customer_id=99999", headers=auth_headers
    )
    assert resp.json()["total"] == 0

    resp = await client.get("/api/reports/employee-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["order_count"] == 3
    assert resp.json()["items"][0]["customer_count"] == 1

    resp = await client.get("/api/reports/product-summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"][0]["sold_quantity"] == 22
    assert resp.json()["items"][0]["sales_amount"] == 330.0

    resp = await client.get("/api/reports/order-detail?page=1&size=10", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 3
    row = resp.json()["items"][0]
    assert row["customer_name"] == "测试医院"
    assert row["product_name"] == "测试药品"

    resp = await client.get(
        "/api/reports/order-detail?customer_id=%d&page=1&size=10" % ids["customer_id"],
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/api/reports/inventory-status", headers=auth_headers)
    assert resp.status_code == 200
    assert any(i["product_name"] == "测试药品" for i in resp.json()["items"])

    resp = await client.get("/api/reports/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["today_order_count"] == 3
    assert body["today_sales_amount"] == 330.0
    assert body["month_order_count"] == 3
    assert body["month_sales_amount"] == 330.0


async def test_report_entity_filters(client: AsyncClient, auth_headers: dict, ids: dict):
    """三个报表页的实体筛选（统一业务对象控件传的是主键）。

    筛选维度只取报表自身行数据带得动的：商品汇总的行是商品（商品 / 分类 / 厂家），
    库存状态的行是「仓库 × 商品」（同上），订单明细的行是订单行（另有客户）。
    """
    await _seed_orders(client, auth_headers, ids)
    product_params = {
        "product_id": ids["product_id"],
        "category_id": ids["category_id"],
        "manufacturer_id": ids["manufacturer_id"],
    }

    for path, expected_total, params in [
        ("/api/reports/product-summary", 1, product_params),
        ("/api/reports/order-detail", 3, {**product_params, "customer_id": ids["customer_id"]}),
        ("/api/reports/inventory-status", 1, product_params),
    ]:
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == expected_total, path

        for param, value in params.items():
            resp = await client.get(
                f"{path}?{param}={value}&page=1&size=10", headers=auth_headers
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["total"] == expected_total, f"{path}?{param}"

        # 未命中的主键必须返回 0 条（防止参数被静默忽略）
        resp = await client.get(
            f"{path}?product_id=99999&page=1&size=10", headers=auth_headers
        )
        assert resp.json()["total"] == 0, path

    # 客户筛选只出现在行上带客户的订单明细
    resp = await client.get(
        f"/api/reports/order-detail?customer_id={ids['customer_id']}", headers=auth_headers
    )
    assert resp.json()["total"] == 3
    resp = await client.get(
        "/api/reports/order-detail?customer_id=99999", headers=auth_headers
    )
    assert resp.json()["total"] == 0

    resp = await client.get(
        f"/api/reports/product-summary?category_id=99999", headers=auth_headers
    )
    assert resp.json()["total"] == 0
    resp = await client.get(
        f"/api/reports/order-detail?manufacturer_id=99999", headers=auth_headers
    )
    assert resp.json()["total"] == 0


async def test_order_detail_by_order_no(client: AsyncClient, auth_headers: dict, ids: dict):
    """订单明细按单号查询（最常用的入口）：完整单号、片段都要能命中，通配符要转义。"""
    await _seed_orders(client, auth_headers, ids)

    first = (
        await client.get("/api/reports/order-detail?page=1&size=1", headers=auth_headers)
    ).json()
    order_no = first["items"][0]["order_no"]

    resp = await client.get(
        "/api/reports/order-detail", params={"order_no": order_no}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["order_no"] == order_no

    # 只输入单号片段（末 4 位）也要命中
    resp = await client.get(
        "/api/reports/order-detail", params={"order_no": order_no[-4:]}, headers=auth_headers
    )
    assert resp.json()["total"] >= 1
    assert all(i["order_no"].endswith(order_no[-4:]) for i in resp.json()["items"])

    resp = await client.get(
        "/api/reports/order-detail",
        params={"order_no": "NO-SUCH-ORDER"},
        headers=auth_headers,
    )
    assert resp.json()["total"] == 0

    # `%` 是 LIKE 通配符，必须转义，否则会命中全部 3 行
    resp = await client.get(
        "/api/reports/order-detail", params={"order_no": "%"}, headers=auth_headers
    )
    assert resp.json()["total"] == 0
