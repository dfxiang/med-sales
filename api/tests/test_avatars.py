"""头像相关测试：规范化、匿名读取、白名单越权、存储异常。

对象存储用内存 fake 替身替换（通过依赖注入 `get_storage` 覆盖），
不依赖真实 MinIO；真实链路在 `frontend/tests/live/` 回归。
"""

import io
import random
import re

import pytest
from PIL import Image

from app.core.storage import get_storage
from app.main import app
from app.services.avatar import (
    AVATAR_PREFIX,
    DEFAULT_AVATAR_KEY,
    ensure_default_avatar,
)

AVATAR_URL_RE = re.compile(r"^/api/avatars/(?:default\.png|u[0-9]+-[0-9a-f]{32}\.png)$")


class FakeStorage:
    """内存对象存储替身。"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_put = False

    async def put_object(self, key: str, data: bytes, content_type: str | None = None) -> None:
        if self.fail_put:
            raise RuntimeError("storage down")
        self.objects[key] = data

    async def get_object(self, key: str) -> bytes:
        return self.objects[key]

    async def get_object_or_none(self, key: str) -> bytes | None:
        return self.objects.get(key)

    async def head_object(self, key: str) -> bool:
        return key in self.objects

    async def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest.fixture
def fake_storage(client) -> FakeStorage:
    storage = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: storage
    return storage


def _image_bytes(fmt: str, size: tuple[int, int] = (300, 200), frames: int = 1) -> bytes:
    image = Image.new("RGBA", size, (10, 120, 200, 255))
    for x in range(0, size[0], 10):  # 加点纹理，避免内容过于一致
        for y in range(0, size[1], 10):
            image.putpixel((x, y), (255, 200, 0, 255))
    buffer = io.BytesIO()
    if fmt in {"JPEG"}:  # JPEG 不支持 alpha 通道
        image = image.convert("RGB")
    if fmt == "GIF" and frames > 1:
        image.save(buffer, format=fmt, save_all=True, append_images=[image], duration=100)
    else:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


async def _upload(client, auth_headers: dict, data: bytes, filename: str):
    return await client.put(
        "/api/auth/me/avatar",
        files={"file": (filename, data, "application/octet-stream")},
        headers=auth_headers,
    )


@pytest.mark.parametrize(
    ("fmt", "filename"),
    [
        ("PNG", "a.png"),
        ("JPEG", "a.jpg"),
        ("BMP", "a.bmp"),
        ("WEBP", "a.webp"),
        ("GIF", "a.gif"),
    ],
)
async def test_avatar_upload_normalizes_to_256_png(
    client, auth_headers, fake_storage: FakeStorage, fmt: str, filename: str
):
    """五种允许格式都能上传，且统一规范化为 256×256 PNG。"""
    frames = 2 if fmt == "GIF" else 1
    resp = await _upload(client, auth_headers, _image_bytes(fmt, frames=frames), filename)
    assert resp.status_code == 200, resp.text
    avatar_url = resp.json()["avatar_url"]
    assert AVATAR_URL_RE.match(avatar_url), avatar_url

    key = f"{AVATAR_PREFIX}{avatar_url.rsplit('/', 1)[-1]}"
    stored = fake_storage.objects[key]
    with Image.open(io.BytesIO(stored)) as image:
        assert image.format == "PNG"
        assert image.size == (256, 256)


async def test_avatar_upload_accepts_non_square_source(
    client, auth_headers, fake_storage: FakeStorage
):
    """竖图 / 横图都能通过 cover 裁切得到正方形头像。"""
    resp = await _upload(client, auth_headers, _image_bytes("PNG", (120, 400)), "tall.png")
    assert resp.status_code == 200, resp.text
    key = f"{AVATAR_PREFIX}{resp.json()['avatar_url'].rsplit('/', 1)[-1]}"
    with Image.open(io.BytesIO(fake_storage.objects[key])) as image:
        assert image.size == (256, 256)


async def test_avatar_anonymous_read_headers_and_304(
    client, auth_headers, fake_storage: FakeStorage
):
    """匿名可读 + 缓存头 + ETag/304。"""
    resp = await _upload(client, auth_headers, _image_bytes("PNG"), "a.png")
    url = resp.json()["avatar_url"]

    # 注意：不带任何 Authorization 头，模拟浏览器 <img> 直接加载
    anon = await client.get(url)
    assert anon.status_code == 200
    assert anon.headers["content-type"] == "image/png"
    assert "immutable" in anon.headers["cache-control"]
    assert anon.headers["x-content-type-options"] == "nosniff"
    etag = anon.headers["etag"]

    cached = await client.get(url, headers={"If-None-Match": etag})
    assert cached.status_code == 304


async def test_default_avatar_is_initialized_lazily(
    client, fake_storage: FakeStorage, auth_headers
):
    """默认头像：未写入对象存储时，匿名接口懒初始化后仍能返回 200。"""
    assert DEFAULT_AVATAR_KEY not in fake_storage.objects
    resp = await client.get("/api/avatars/default.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert DEFAULT_AVATAR_KEY in fake_storage.objects
    with Image.open(io.BytesIO(fake_storage.objects[DEFAULT_AVATAR_KEY])) as image:
        assert image.size == (256, 256)


async def test_unset_avatar_falls_back_to_default(client, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] == "/api/avatars/default.png"


async def test_avatar_upload_rejects_invalid_payloads(
    client, auth_headers, fake_storage: FakeStorage
):
    # 不是图片（纯文本）
    resp = await _upload(client, auth_headers, b"hello world", "a.png")
    assert resp.status_code == 400
    assert "不是有效的图片" in resp.json()["detail"]

    # 扩展名不在白名单
    resp = await _upload(client, auth_headers, _image_bytes("PNG"), "a.svg")
    assert resp.status_code == 400
    assert "不支持的图片格式" in resp.json()["detail"]

    # 空文件
    resp = await _upload(client, auth_headers, b"", "a.png")
    assert resp.status_code == 400

    # 解压炸弹（超单边上限）
    bomb = io.BytesIO()
    Image.new("1", (20000, 20000)).save(bomb, format="PNG")
    resp = await _upload(client, auth_headers, bomb.getvalue(), "big.png")
    assert resp.status_code == 400
    assert "分辨率过大" in resp.json()["detail"]


async def test_avatar_upload_rejects_oversize_file(
    client, auth_headers, fake_storage: FakeStorage
):
    """>1MB 直接 413（用随机噪声 PNG 保证压缩后仍超限）。"""
    random.seed(20261012)
    width = height = 1200
    noise = Image.new("RGB", (width, height))
    noise.putdata(
        [
            (random.randrange(256), random.randrange(256), random.randrange(256))
            for _ in range(width * height)
        ]
    )
    buffer = io.BytesIO()
    noise.save(buffer, format="PNG")
    payload = buffer.getvalue()
    assert len(payload) > 1024 * 1024

    resp = await _upload(client, auth_headers, payload, "huge.png")
    assert resp.status_code == 413
    assert "1MB" in resp.json()["detail"]


async def test_avatar_upload_requires_auth(client):
    resp = await client.put(
        "/api/auth/me/avatar", files={"file": ("a.png", _image_bytes("PNG"), "image/png")}
    )
    assert resp.status_code == 401


async def test_avatar_storage_unavailable_returns_503(
    client, auth_headers, fake_storage: FakeStorage
):
    fake_storage.fail_put = True
    resp = await _upload(client, auth_headers, _image_bytes("PNG"), "a.png")
    assert resp.status_code == 503
    assert "对象存储不可用" in resp.json()["detail"]


async def test_avatar_delete_restores_default_and_removes_object(
    client, auth_headers, fake_storage: FakeStorage
):
    resp = await _upload(client, auth_headers, _image_bytes("PNG"), "a.png")
    url = resp.json()["avatar_url"]
    key = f"{AVATAR_PREFIX}{url.rsplit('/', 1)[-1]}"
    assert key in fake_storage.objects

    deleted = await client.delete("/api/auth/me/avatar", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["avatar_url"] == "/api/avatars/default.png"
    assert key not in fake_storage.objects  # 旧对象已清理
    assert (await client.get(url)).status_code == 404

    # 幂等：本来就没有头像时重复删除也是 200
    again = await client.delete("/api/auth/me/avatar", headers=auth_headers)
    assert again.status_code == 200


async def test_avatar_replace_removes_previous_object(
    client, auth_headers, fake_storage: FakeStorage
):
    first = await _upload(client, auth_headers, _image_bytes("PNG"), "a.png")
    first_key = f"{AVATAR_PREFIX}{first.json()['avatar_url'].rsplit('/', 1)[-1]}"
    second = await _upload(client, auth_headers, _image_bytes("JPEG"), "b.jpg")
    second_key = f"{AVATAR_PREFIX}{second.json()['avatar_url'].rsplit('/', 1)[-1]}"

    assert first_key != second_key
    assert first_key not in fake_storage.objects
    assert second_key in fake_storage.objects
    assert (await client.get(first.json()["avatar_url"])).status_code == 404


@pytest.mark.parametrize(
    "filename",
    [
        "gsp/certificates/1/deadbeef.pdf",  # 越权读取证照
        "..%2Fusers.png",
        "u1-0123456789abcdef.png",  # 十六进制长度不足 32
        "u1-0123456789ABCDEF0123456789ABCDEF.png",  # 大写不匹配
        "u1-0123456789abcdef0123456789abcdef.gif",  # 非 png
        "admin.png",
    ],
)
async def test_avatar_anonymous_read_whitelist(client, fake_storage: FakeStorage, filename: str):
    """非白名单文件名一律 404：匿名接口不能变成任意对象下载器。"""
    fake_storage.objects[f"{AVATAR_PREFIX}{filename}"] = b"secret"
    fake_storage.objects["gsp/certificates/1/deadbeef.pdf"] = b"certificate"
    resp = await client.get(f"/api/avatars/{filename}")
    assert resp.status_code == 404


async def test_ensure_default_avatar_is_idempotent(fake_storage: FakeStorage):
    assert await ensure_default_avatar(fake_storage) is True
    first = dict(fake_storage.objects)
    assert DEFAULT_AVATAR_KEY in first
    # 第二次调用不应重写（head_object 命中即返回）
    assert await ensure_default_avatar(fake_storage) is True
    assert fake_storage.objects == first
