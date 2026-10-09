from typing import Annotated
import hmac

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.core.config import settings
from app.core.permissions import is_superuser, permission_codes
from app.core.security import create_access_token, verify_password
from app.models.system import AuditLog, Role, User
from app.schemas.system import GetTokenByApiKey, LoginRequest, MeOut, TokenOut

router = APIRouter()


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
    me_out = MeOut.model_validate(current_user)
    me_out.permissions = sorted(permission_codes(current_user))
    me_out.is_superuser = is_superuser(current_user)
    return me_out


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
