from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
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


async def get_page_params(
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    size: Annotated[int, Query(ge=1, le=200, description="每页条数，1-200")] = 20,
) -> PageParams:
    """分页查询参数依赖（page/size）。

    参数约束声明在 FastAPI 查询参数上，非法取值（如 page=0、size=500）会由
    FastAPI 直接返回 422，而不是在校验模型时抛 500。
    """
    return PageParams(page=page, size=size)
