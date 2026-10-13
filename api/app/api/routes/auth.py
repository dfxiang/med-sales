import hmac
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, StorageDep
from app.core.database import get_db
from app.core.config import settings
from app.core.permissions import is_superuser, permission_codes
from app.core.security import create_access_token, hash_password, verify_password
from app.models.system import AuditLog, Role, User
from app.schemas.common import Message
from app.schemas.system import (
    GetTokenByApiKey,
    LoginRequest,
    MeOut,
    PasswordChange,
    ProfileUpdate,
    TokenOut,
)
from app.services.avatar import (
    AVATAR_MAX_BYTES,
    AVATAR_SUFFIXES,
    AvatarValidationError,
    new_avatar_key,
    normalize_avatar,
)
from app.services.avatar import DEFAULT_AVATAR_FILENAME  # noqa: F401  （供文档/测试引用）

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]
PROFILE_FIELD_LABELS = (
    ("display_name", "显示名称"),
    ("phone", "电话"),
    ("email", "邮箱"),
)


def _me_out(user: User) -> MeOut:
    """组装当前用户信息（含扁平化权限编码与只读 avatar_url）。"""
    me_out = MeOut.model_validate(user)
    me_out.permissions = sorted(permission_codes(user))
    me_out.is_superuser = is_superuser(user)
    return me_out


async def _reload_user(db: AsyncSession, user_id: int) -> User:
    """重新加载用户（连带角色与权限），保证 MeOut 中的角色信息完整。"""
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    assert user is not None  # 当前登录用户必然存在
    return user


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """按上限读取上传内容：超限立即中止，不把超限内容读进内存。"""
    if file.size is not None and file.size > limit:
        raise HTTPException(status_code=413, detail="头像文件过大（上限 1MB）")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail="头像文件过大（上限 1MB）")
        chunks.append(chunk)
    return b"".join(chunks)


async def _delete_quietly(storage, key: str) -> None:
    """尽力删除旧头像对象：失败只记日志，不影响请求结果。"""
    try:
        await storage.delete_object(key)
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        import logging

        logging.getLogger(__name__).warning("删除旧头像对象失败 %s: %s", key, exc)


@router.post("/login", response_model=TokenOut, summary="登录获取令牌")
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenOut:
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.username == payload.username)
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    db.add(
        AuditLog(user_id=user.id, username=user.username, action="login", module="auth", detail="用户登录")
    )
    await db.commit()
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=MeOut, summary="获取当前登录用户信息（含权限编码）")
async def me(current_user: CurrentUser) -> MeOut:
    """返回当前用户的角色与扁平化权限编码，前端据此控制菜单、路由与按钮。"""
    return _me_out(current_user)


@router.put("/me", response_model=MeOut, summary="更新当前用户个人资料")
async def update_me(payload: ProfileUpdate, current_user: CurrentUser, db: Db) -> MeOut:
    """自助改资料：只能改自己、只能改"除用户名外"的资料字段。"""
    data = payload.model_dump(exclude_unset=True)
    if "display_name" in data and not (data["display_name"] or "").strip():
        raise HTTPException(status_code=400, detail="显示名称不能为空")
    for field, value in data.items():
        setattr(current_user, field, value)
    changed = [label for field, label in PROFILE_FIELD_LABELS if field in data]
    if changed:
        db.add(
            AuditLog(
                user_id=current_user.id,
                username=current_user.username,
                action="update",
                module="auth",
                detail=f"更新个人资料：{'、'.join(changed)}",
            )
        )
    await db.commit()
    return _me_out(await _reload_user(db, current_user.id))


@router.put("/me/password", response_model=Message, summary="修改当前用户登录密码")
async def change_my_password(
    payload: PasswordChange, current_user: CurrentUser, db: Db
) -> Message:
    """自助改密：校验原密码 + 新密码两次确认一致，并记录审计日志。"""
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的新密码不一致")
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    current_user.password_hash = hash_password(payload.new_password)
    db.add(
        AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action="update",
            module="auth",
            detail="修改登录密码",
        )
    )
    await db.commit()
    return Message(message="密码已修改")


@router.put("/me/avatar", response_model=MeOut, summary="上传/更换当前用户头像")
async def upload_my_avatar(
    current_user: CurrentUser,
    db: Db,
    storage: StorageDep,
    file: Annotated[UploadFile, File(description="头像图片：jpg/png/bmp/webp/gif，≤1MB")],
) -> MeOut:
    """自助上传头像：服务端统一规范化为 256×256 PNG 后再入库（见设计文档 §5.5）。"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in AVATAR_SUFFIXES:
        raise HTTPException(
            status_code=400, detail="不支持的图片格式（支持 jpg/png/bmp/webp/gif）"
        )
    data = await _read_limited(file, AVATAR_MAX_BYTES)
    try:
        normalized = normalize_avatar(data)
    except AvatarValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    key = new_avatar_key(current_user.id)
    old_key = current_user.avatar_key
    try:
        await storage.put_object(key, normalized, "image/png")
    except Exception as exc:  # pragma: no cover - 依赖真实存储
        raise HTTPException(status_code=503, detail=f"对象存储不可用：{exc}") from exc

    # 先传对象、后写库：写库失败最坏只留一个不可达的孤儿对象
    current_user.avatar_key = key
    db.add(
        AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            action="update",
            module="auth",
            detail="更新头像",
        )
    )
    await db.commit()
    if old_key and old_key != key:
        await _delete_quietly(storage, old_key)
    return _me_out(await _reload_user(db, current_user.id))


@router.delete("/me/avatar", response_model=MeOut, summary="恢复默认头像")
async def delete_my_avatar(
    current_user: CurrentUser, db: Db, storage: StorageDep
) -> MeOut:
    """清空头像（回落默认头像）；幂等：本来就没有头像时不写审计。"""
    old_key = current_user.avatar_key
    if old_key:
        current_user.avatar_key = None
        db.add(
            AuditLog(
                user_id=current_user.id,
                username=current_user.username,
                action="update",
                module="auth",
                detail="恢复默认头像",
            )
        )
        await db.commit()
        await _delete_quietly(storage, old_key)
    return _me_out(await _reload_user(db, current_user.id))


@router.post("/token", response_model=TokenOut, summary="通过 API Key + 用户 ID 获取令牌（系统对接）")
async def get_token_by_api_key(
    payload: GetTokenByApiKey,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenOut:
    """系统间对接：使用环境变量配置的 API Key + 用户 ID 换取 JWT，效果等同登录。"""
    configured_keys = settings.sys_api_key_list
    if not configured_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="系统未配置 API Key（请设置环境变量 SYS_API_KEYS）",
        )
    matched = any(
        hmac.compare_digest(payload.api_key, configured)
        for configured in configured_keys
    )
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 无效",
        )

    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == payload.user_id)
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被停用",
        )

    db.add(
        AuditLog(
            user_id=user.id,
            username=user.username,
            action="token",
            module="auth",
            detail=f"通过 API Key 为 user_id={user.id} 签发令牌",
        )
    )
    await db.commit()
    return TokenOut(access_token=create_access_token(user.id))
