from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import code_label, has_permission
from app.core.security import decode_access_token
from app.core.storage import ObjectStorage, get_storage
from app.models.system import Role
from app.models.system import User
from app.schemas.common import PageParams

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证凭据无效或已过期",
        )
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被停用",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

# 对象存储依赖：路由通过依赖注入取用（便于单测替换为内存实现）
StorageDep = Annotated[ObjectStorage, Depends(get_storage)]


def require_permission(*codes: str):
    """依赖工厂：要求当前用户具备其中任一权限，否则 403。

    用法（挂在路由装饰器上，不动函数签名）::

        @router.get("/users", dependencies=[Depends(require_permission("system:user:view"))])

    内置权限 `all` 为通配权限，命中后直接放行。
    """
    if not codes:
        raise ValueError("require_permission 至少需要一个权限编码")
    required = tuple(codes)

    async def _check(current_user: CurrentUser) -> User:
        if not has_permission(current_user, *required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足：需要「" + "」或「".join(code_label(c) for c in required) + "」权限",
            )
        return current_user

    # 供 scripts/gen_api_docs.py 生成「所需权限」列
    _check.__permission_codes__ = required
    return _check


async def get_page_params(
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    size: Annotated[int, Query(ge=1, le=1000, description="每页条数，1-1000")] = 20,
) -> PageParams:
    """分页查询参数依赖（page/size）。

    参数约束声明在 FastAPI 查询参数上，非法取值（如 page=0、size=1001）会由
    FastAPI 直接返回 422，而不是在校验模型时抛 500。
    """
    return PageParams(page=page, size=size)
