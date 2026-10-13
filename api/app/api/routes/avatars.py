"""头像读取接口（**匿名开放**，无需令牌）。

安全边界只有两条，必须同时成立（见 `docs/用户资料扩展设计.md` §5.4）：

1. 文件名白名单正则：只认 `default.png` 与 `u{用户ID}-{32 位十六进制}.png`；
2. 对象键前缀由服务端固定为 `avatar/`，调用方无法影响。

任何一条被放宽，匿名接口就可能变成"任意对象下载器"——同一个 bucket 里还存着
GSP 证照扫描件（`gsp/certificates/...`）。因此不匹配一律返回 404（而非 403，
避免通过错误码区分"不存在"与"无权限"，泄露 key 空间）。
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.deps import StorageDep
from app.services.avatar import (
    DEFAULT_AVATAR_FILENAME,
    avatar_key_from_filename,
    ensure_default_avatar,
    is_avatar_filename,
)

router = APIRouter()

# 头像文件名是随机的（换头像即换 URL），内容不会再变，可以放心长缓存
CACHE_CONTROL = "public, max-age=604800, immutable"


@router.get("/{filename}", summary="读取头像（匿名访问）")
async def read_avatar(filename: str, storage: StorageDep, request: Request) -> Response:
    if not is_avatar_filename(filename):
        raise HTTPException(status_code=404, detail="头像不存在")

    key = avatar_key_from_filename(filename)
    data = await _get_object_or_503(storage, key)
    if data is None and filename == DEFAULT_AVATAR_FILENAME:
        # 懒初始化兜底：默认头像尚未写入对象存储时补一次
        await ensure_default_avatar(storage)
        data = await _get_object_or_503(storage, key)
    if data is None:
        raise HTTPException(status_code=404, detail="头像不存在")

    etag = '"' + hashlib.md5(data).hexdigest() + '"'
    headers = {
        "Cache-Control": CACHE_CONTROL,
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    # 存储里只有服务端规范化后的 PNG，因此媒体类型恒定，不依赖对象元数据
    return Response(content=data, media_type="image/png", headers=headers)


async def _get_object_or_503(storage, key: str) -> bytes | None:
    try:
        return await storage.get_object_or_none(key)
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        raise HTTPException(status_code=503, detail=f"对象存储不可用：{exc}") from exc
