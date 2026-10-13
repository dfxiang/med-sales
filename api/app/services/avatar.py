"""头像处理：校验、规范化（256×256 PNG）、默认头像初始化。

设计依据见 `docs/用户资料扩展设计.md` 第五章，要点：

1. **上传的原始字节不会原样存回对象存储**：统一解码 → 居中裁切缩放 → 重新编码 PNG。
   这样存储里永远只有真实 PNG（杜绝改名的 HTML/SVG/polyglot 被当作图片回吐），
   同时丢弃 EXIF（含 GPS 定位）等元数据。
2. **匿名读取接口的安全边界**只有两条：文件名白名单正则 + 固定 `avatar/` 前缀。
   两者同时成立才能保证匿名接口不会变成"任意对象下载器"（bucket 里还有 GSP 证照扫描件）。
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.core.storage import ObjectStorage

logger = logging.getLogger(__name__)

AVATAR_PREFIX = "avatar/"
DEFAULT_AVATAR_FILENAME = "default.png"
DEFAULT_AVATAR_KEY = f"{AVATAR_PREFIX}{DEFAULT_AVATAR_FILENAME}"

AVATAR_SIZE = 256
AVATAR_MAX_BYTES = 1024 * 1024
AVATAR_MAX_EDGE = 10_000
# 允许的上传格式（以 Pillow 实际解码结果为准；扩展名只用于快速拒绝）
AVATAR_FORMATS = {"JPEG", "PNG", "BMP", "WEBP", "GIF"}
AVATAR_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}

# 匿名读取白名单：默认头像 + 用户头像（u{用户ID}-{32 位十六进制}.png）
AVATAR_FILENAME_RE = re.compile(r"^(?:default\.png|u[0-9]{1,9}-[0-9a-f]{32}\.png)$")

_ASSET_PATH = Path(__file__).resolve().parent.parent / "assets" / "avatar-default.png"


class AvatarValidationError(Exception):
    """头像校验失败：携带对外返回的 HTTP 状态码与中文提示。"""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def is_avatar_filename(filename: str) -> bool:
    """文件名是否在白名单内（匿名读取接口的唯一入口校验）。"""
    return bool(AVATAR_FILENAME_RE.match(filename))


def avatar_filename(avatar_key: str | None) -> str:
    """对象键 → 对外文件名；未设置头像时回落默认头像。"""
    if not avatar_key:
        return DEFAULT_AVATAR_FILENAME
    return avatar_key.rsplit("/", 1)[-1]


def avatar_url_for(avatar_key: str | None) -> str:
    return f"/api/avatars/{avatar_filename(avatar_key)}"


def avatar_key_from_filename(filename: str) -> str:
    """白名单文件名 → 对象键（前缀由服务端固定，调用方无法影响）。"""
    return f"{AVATAR_PREFIX}{filename}"


def new_avatar_key(user_id: int) -> str:
    """随机对象键：随机名天然充当"缓存版本号"，换头像即换 URL。"""
    return f"{AVATAR_PREFIX}u{user_id}-{uuid4().hex}.png"


def _cover_resize(image: Image.Image) -> Image.Image:
    """等比缩放 + 居中裁切，产出正好 AVATAR_SIZE×AVATAR_SIZE 的 RGBA 图。"""
    if getattr(image, "is_animated", False):  # GIF 动图只取首帧
        image.seek(0)
    converted = image.convert("RGBA")
    width, height = converted.size
    scale = AVATAR_SIZE / min(width, height)
    resized_size = (
        max(AVATAR_SIZE, round(width * scale)),
        max(AVATAR_SIZE, round(height * scale)),
    )
    resized = converted.resize(resized_size, Image.Resampling.LANCZOS)
    left = (resized_size[0] - AVATAR_SIZE) // 2
    top = (resized_size[1] - AVATAR_SIZE) // 2
    return resized.crop((left, top, left + AVATAR_SIZE, top + AVATAR_SIZE))


def normalize_avatar(data: bytes) -> bytes:
    """校验并规范化头像，返回可直接入库的 PNG 字节。"""
    if not data:
        raise AvatarValidationError("头像文件为空")
    if len(data) > AVATAR_MAX_BYTES:
        raise AvatarValidationError("头像文件过大（上限 1MB）", status_code=413)

    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = (image.format or "").upper()
            if image_format not in AVATAR_FORMATS:
                raise AvatarValidationError(
                    "不支持的图片格式（支持 jpg/png/bmp/webp/gif）"
                )
            if max(image.size) > AVATAR_MAX_EDGE:
                raise AvatarValidationError("图片分辨率过大")
            normalized = _cover_resize(image)
    except AvatarValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise AvatarValidationError("图片分辨率过大") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise AvatarValidationError("不是有效的图片文件") from exc

    output = io.BytesIO()
    normalized.save(output, format="PNG", optimize=True)
    return output.getvalue()


def default_avatar_bytes() -> bytes:
    """仓库内置的默认头像（256×256 PNG）。"""
    return _ASSET_PATH.read_bytes()


async def ensure_default_avatar(storage: ObjectStorage) -> bool:
    """确保默认头像已初始化到对象存储：幂等、失败仅告警、不阻塞启动。"""
    try:
        if await storage.head_object(DEFAULT_AVATAR_KEY):
            return True
        await storage.put_object(DEFAULT_AVATAR_KEY, default_avatar_bytes(), "image/png")
        logger.info("默认头像已初始化：%s", DEFAULT_AVATAR_KEY)
        return True
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        logger.warning("默认头像初始化失败：%s", exc)
        return False
