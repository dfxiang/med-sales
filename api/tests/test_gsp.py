from datetime import date, timedelta

import pytest
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


# ----------------------------- 首营资质闭环 -----------------------------
def _cert_payload(ids: dict, **overrides) -> dict:
    payload = {
        "entity_type": "customer",
        "entity_id": ids["customer_id"],
        "cert_type": "药品经营许可证",
        "cert_no": "沪A-CLOSED-LOOP",
        "valid_from": "2026-01-01",
        "valid_to": "2029-01-01",
    }
    payload.update(overrides)
    return payload


async def test_certificate_review_flow(client: AsyncClient, auth_headers: dict, ids: dict):
    """新建证照默认待审核，审核通过/驳回后状态正确流转。"""
    resp = await client.post(
        "/api/gsp/certificates", headers=auth_headers, json=_cert_payload(ids)
    )
    assert resp.status_code == 201, resp.text
    cert = resp.json()
    assert cert["review_status"] == "待审核"
    assert cert["effective_status"] == "待审核"
    cid = cert["id"]

    # 审核通过
    resp = await client.post(
        f"/api/gsp/certificates/{cid}/review",
        headers=auth_headers,
        json={"action": "approve", "remark": "资质齐全"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review_status"] == "已通过"
    assert resp.json()["effective_status"] == "有效"

    # 关键信息变更后需重新审核
    resp = await client.put(
        f"/api/gsp/certificates/{cid}", headers=auth_headers, json={"cert_no": "沪A-CHANGED"}
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "待审核"

    # 驳回
    resp = await client.post(
        f"/api/gsp/certificates/{cid}/review",
        headers=auth_headers,
        json={"action": "reject", "remark": "证号与扫描件不符"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["review_status"] == "已驳回"
    assert body["effective_status"] == "已驳回"
    assert body["review_remark"] == "证号与扫描件不符"


async def test_qualification_profile_view(client: AsyncClient, auth_headers: dict, ids: dict):
    """资质档案接口返回主体名称、准入结论与问题清单。"""
    await client.post(
        "/api/gsp/certificates",
        headers=auth_headers,
        json=_cert_payload(ids, valid_to="2029-01-01"),
    )
    resp = await client.get(
        f"/api/gsp/qualification/customer/{ids['customer_id']}", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entity_name"] == "测试医院"
    assert body["has_profile"] is True
    # 待审核证照阻断交易
    assert body["compliant"] is False
    assert body["blocking"][0]["kind"] == "待审核"
    assert body["certificates"][0]["attachment_count"] == 0


async def test_qualification_blocks_sales_order(
    client: AsyncClient, auth_headers: dict, ids: dict
):
    """闭环关键：证照过期则禁止下单，换证审核通过后恢复。"""
    expired = await client.post(
        "/api/gsp/certificates",
        headers=auth_headers,
        json=_cert_payload(ids, valid_to="2020-01-01"),
    )
    cid = expired.json()["id"]
    await client.post(
        f"/api/gsp/certificates/{cid}/review", headers=auth_headers, json={"action": "approve"}
    )

    payload = {
        "customer_id": ids["customer_id"],
        "employee_id": ids["employee_id"],
        "warehouse_id": ids["warehouse_id"],
        "order_date": "2026-08-10",
        "items": [{"product_id": ids["product_id"], "quantity": 1, "discount_rate": 0}],
    }
    resp = await client.post("/api/sales-orders", headers=auth_headers, json=payload)
    assert resp.status_code == 400, resp.text
    assert "GSP 资质校验未通过" in resp.json()["detail"]
    assert "有效期异常" in resp.json()["detail"]

    # 换证：更新有效期后重新审核通过
    await client.put(
        f"/api/gsp/certificates/{cid}", headers=auth_headers, json={"valid_to": "2030-01-01"}
    )
    await client.post(
        f"/api/gsp/certificates/{cid}/review", headers=auth_headers, json={"action": "approve"}
    )
    resp = await client.post("/api/sales-orders", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text

    # 拦截记录进入审计日志
    resp = await client.get("/api/audit-logs?module=gsp&page=1&size=20", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    actions = {row["action"] for row in resp.json()["items"]}
    assert "block" in actions


async def test_attachment_versioning(
    client: AsyncClient, auth_headers: dict, ids: dict, monkeypatch: pytest.MonkeyPatch
):
    """换证上传新扫描件时旧版本转为历史版本，仅当前版本默认可见。"""
    from app.api.routes import gsp as gsp_routes

    store: dict[str, bytes] = {}

    async def fake_put(key: str, data: bytes, content_type: str | None = None) -> None:
        store[key] = data

    async def fake_get(key: str) -> bytes:
        return store[key]

    async def fake_delete(key: str) -> None:
        store.pop(key, None)

    monkeypatch.setattr(gsp_routes.storage, "put_object", fake_put)
    monkeypatch.setattr(gsp_routes.storage, "get_object", fake_get)
    monkeypatch.setattr(gsp_routes.storage, "delete_object", fake_delete)

    cert = await client.post(
        "/api/gsp/certificates", headers=auth_headers, json=_cert_payload(ids)
    )
    cid = cert.json()["id"]

    for name in ("旧证.pdf", "新证.pdf"):
        resp = await client.post(
            f"/api/gsp/certificates/{cid}/attachments",
            headers=auth_headers,
            files={"file": (name, b"%PDF-1.4 demo", "application/pdf")},
        )
        assert resp.status_code == 201, resp.text

    resp = await client.get(f"/api/gsp/certificates/{cid}/attachments", headers=auth_headers)
    assert resp.status_code == 200
    current = resp.json()
    assert len(current) == 1
    assert current[0]["file_name"] == "新证.pdf"
    assert current[0]["version"] == 2
    assert current[0]["is_current"] is True

    resp = await client.get(
        f"/api/gsp/certificates/{cid}/attachments?include_history=true", headers=auth_headers
    )
    assert len(resp.json()) == 2

    # 附件数计入证照列表
    resp = await client.get(
        f"/api/gsp/certificates?entity_type=customer&entity_id={ids['customer_id']}",
        headers=auth_headers,
    )
    assert resp.json()["items"][0]["attachment_count"] == 2

    # 下载留痕
    attachment_id = current[0]["id"]
    resp = await client.get(f"/api/gsp/attachments/{attachment_id}/download", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 demo"


async def test_alerts_and_summary(client: AsyncClient, auth_headers: dict, ids: dict):
    """预警中心：证照与批次近效期分级统计。"""
    soon = (date.today() + timedelta(days=20)).isoformat()
    await client.post(
        "/api/gsp/certificates",
        headers=auth_headers,
        json=_cert_payload(ids, cert_type="营业执照", valid_to=soon),
    )
    await client.post(
        "/api/gsp/batches",
        headers=auth_headers,
        json={"product_id": ids["product_id"], "batch_no": "B-ALERT-1", "expiry_date": "2020-01-01"},
    )

    resp = await client.get("/api/gsp/alerts?page=1&size=20", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    levels = {row["level"] for row in body["items"]}
    assert levels == {"已过期", "30天内"}

    resp = await client.get("/api/gsp/alerts?level=30天内", headers=auth_headers)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["category"] == "certificate"

    resp = await client.get("/api/gsp/alerts/summary", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert summary["within_30"] == 1
    assert summary["expired"] == 1
    assert summary["certificate_total"] == 1
    assert summary["batch_total"] == 1


async def test_attachment_preview(
    client: AsyncClient, auth_headers: dict, ids: dict, monkeypatch: pytest.MonkeyPatch
):
    """在线预览：接口以 inline 方式回传扫描件，并给出正确的 MIME 类型。"""
    from app.api.routes import gsp as gsp_routes

    store: dict[str, bytes] = {}

    async def fake_put(key: str, data: bytes, content_type: str | None = None) -> None:
        store[key] = data

    async def fake_get(key: str) -> bytes:
        return store[key]

    monkeypatch.setattr(gsp_routes.storage, "put_object", fake_put)
    monkeypatch.setattr(gsp_routes.storage, "get_object", fake_get)

    cert = await client.post(
        "/api/gsp/certificates", headers=auth_headers, json=_cert_payload(ids)
    )
    cid = cert.json()["id"]

    files = [
        ("许可证.jpg", b"\xff\xd8\xff-jpg-bytes", "image/jpeg"),
        ("许可证.png", b"\x89PNG-png-bytes", "image/png"),
        ("许可证.pdf", b"%PDF-1.4 pdf-bytes", "application/pdf"),
        ("质量协议.docx", b"PK-docx-bytes", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ]
    uploaded: dict[str, int] = {}
    for name, content, mime in files:
        resp = await client.post(
            f"/api/gsp/certificates/{cid}/attachments",
            headers=auth_headers,
            files={"file": (name, content, mime)},
        )
        assert resp.status_code == 201, resp.text
        uploaded[name] = resp.json()["id"]

    # 列表返回预览元数据（kind / previewable / media_type）
    resp = await client.get(
        f"/api/gsp/certificates/{cid}/attachments?include_history=true", headers=auth_headers
    )
    meta = {row["file_name"]: row for row in resp.json()}
    assert (meta["许可证.jpg"]["kind"], meta["许可证.jpg"]["previewable"]) == ("image", True)
    assert (meta["许可证.png"]["kind"], meta["许可证.png"]["previewable"]) == ("image", True)
    assert (meta["许可证.pdf"]["kind"], meta["许可证.pdf"]["previewable"]) == ("pdf", True)
    assert meta["许可证.pdf"]["media_type"] == "application/pdf"
    assert (meta["质量协议.docx"]["kind"], meta["质量协议.docx"]["previewable"]) == ("other", False)

    # 预览：inline + 正确 MIME，内容与上传一致
    for name, content, mime in files[:3]:
        resp = await client.get(
            f"/api/gsp/attachments/{uploaded[name]}/preview", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-disposition"].startswith("inline")
        assert resp.headers["content-type"].startswith(mime)
        assert resp.content == content

    # 下载仍为 attachment，且预览/下载都留痕
    resp = await client.get(
        f"/api/gsp/attachments/{uploaded['许可证.pdf']}/download", headers=auth_headers
    )
    assert resp.headers["content-disposition"].startswith("attachment")
    resp = await client.get("/api/audit-logs?module=gsp&page=1&size=50", headers=auth_headers)
    actions = [row["action"] for row in resp.json()["items"]]
    assert "preview" in actions and "download" in actions
