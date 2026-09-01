from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.crud import create_and_commit, delete_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params
from app.core.database import get_db
from app.core.security import hash_password
from app.models.system import (
    AuditLog,
    Permission,
    Role,
    User,
)
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.system import (
    AuditLogOut,
    PermissionCreate,
    PermissionOut,
    PermissionUpdate,
    RoleCreate,
    RoleOut,
    RolePermissionBind,
    RoleUpdate,
    UserCreate,
    UserOut,
    UserRoleBind,
    UserUpdate,
)

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


# ----------------------------- 用户管理 -----------------------------
@router.get("/users", response_model=Page[UserOut], summary="用户列表")
async def list_users(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    keyword: str | None = None,
):
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .order_by(User.id)
    )
    if keyword:
        stmt = stmt.where(User.username.ilike(f"%{keyword}%"))
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/users/{user_id}", response_model=UserOut, summary="用户详情")
async def get_user(user_id: int, db: Db, _: CurrentUser):
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/users", response_model=UserOut, status_code=201, summary="创建用户")
async def create_user(payload: UserCreate, db: Db, current: CurrentUser):
    exists = await db.scalar(select(User).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        employee_id=payload.employee_id,
        is_active=payload.is_active,
    )
    user = await create_and_commit(db, user)
    db.add(
        AuditLog(
            user_id=current.id,
            username=current.username,
            action="create",
            module="system",
            detail=f"创建用户 {user.username}",
        )
    )
    await db.commit()
    await db.refresh(user)
    return await _load_user(db, user.id)


@router.put("/users/{user_id}", response_model=UserOut, summary="更新用户")
async def update_user(user_id: int, payload: UserUpdate, db: Db, _: CurrentUser):
    user = await get_or_404(db, User, user_id, "用户不存在")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        data["password_hash"] = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    await update_and_commit(db, user, data)
    return await _load_user(db, user.id)


@router.delete("/users/{user_id}", response_model=Message, summary="删除用户")
async def delete_user(user_id: int, db: Db, _: CurrentUser):
    user = await get_or_404(db, User, user_id, "用户不存在")
    await delete_and_commit(db, user)
    return Message(message="用户已删除")


@router.post("/users/{user_id}/roles", response_model=UserOut, summary="为用户分配角色")
async def bind_user_roles(user_id: int, payload: UserRoleBind, db: Db, _: CurrentUser):
    user = await get_or_404(db, User, user_id, "用户不存在")
    user.roles = []
    for role_id in payload.role_ids:
        role = await get_or_404(db, Role, role_id, f"角色 {role_id} 不存在")
        user.roles.append(role)
    await db.commit()
    return await _load_user(db, user_id)


# ----------------------------- 角色管理 -----------------------------
@router.get("/roles", response_model=Page[RoleOut], summary="角色列表")
async def list_roles(db: Db, params: Annotated[PageParams, Depends(get_page_params)], _: CurrentUser):
    stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/roles/{role_id}", response_model=RoleOut, summary="角色详情")
async def get_role(role_id: int, db: Db, _: CurrentUser):
    role = await db.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role


@router.post("/roles", response_model=RoleOut, status_code=201, summary="创建角色")
async def create_role(payload: RoleCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Role).where(Role.name == payload.name))
    if exists:
        raise HTTPException(status_code=400, detail="角色名已存在")
    role = await create_and_commit(db, Role(**payload.model_dump()))
    return await _load_role(db, role.id)


@router.put("/roles/{role_id}", response_model=RoleOut, summary="更新角色")
async def update_role(role_id: int, payload: RoleUpdate, db: Db, _: CurrentUser):
    role = await get_or_404(db, Role, role_id, "角色不存在")
    await update_and_commit(db, role, payload.model_dump(exclude_unset=True))
    return await _load_role(db, role.id)


@router.delete("/roles/{role_id}", response_model=Message, summary="删除角色")
async def delete_role(role_id: int, db: Db, _: CurrentUser):
    role = await get_or_404(db, Role, role_id, "角色不存在")
    await delete_and_commit(db, role)
    return Message(message="角色已删除")


@router.post("/roles/{role_id}/permissions", response_model=RoleOut, summary="为角色分配权限")
async def bind_role_permissions(role_id: int, payload: RolePermissionBind, db: Db, _: CurrentUser):
    role = await get_or_404(db, Role, role_id, "角色不存在")
    role.permissions = []
    for permission_id in payload.permission_ids:
        permission = await get_or_404(db, Permission, permission_id, f"权限 {permission_id} 不存在")
        role.permissions.append(permission)
    await db.commit()
    return await _load_role(db, role_id)


# ----------------------------- 权限管理 -----------------------------
@router.get("/permissions", response_model=Page[PermissionOut], summary="权限列表")
async def list_permissions(db: Db, params: Annotated[PageParams, Depends(get_page_params)], _: CurrentUser):
    stmt = select(Permission).order_by(Permission.id)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get("/permissions/{permission_id}", response_model=PermissionOut, summary="权限详情")
async def get_permission(permission_id: int, db: Db, _: CurrentUser):
    return await get_or_404(db, Permission, permission_id, "权限不存在")


@router.post("/permissions", response_model=PermissionOut, status_code=201, summary="创建权限")
async def create_permission(payload: PermissionCreate, db: Db, _: CurrentUser):
    exists = await db.scalar(select(Permission).where(Permission.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="权限编码已存在")
    return await create_and_commit(db, Permission(**payload.model_dump()))


@router.put("/permissions/{permission_id}", response_model=PermissionOut, summary="更新权限")
async def update_permission(permission_id: int, payload: PermissionUpdate, db: Db, _: CurrentUser):
    permission = await get_or_404(db, Permission, permission_id, "权限不存在")
    return await update_and_commit(db, permission, payload.model_dump(exclude_unset=True))


@router.delete("/permissions/{permission_id}", response_model=Message, summary="删除权限")
async def delete_permission(permission_id: int, db: Db, _: CurrentUser):
    permission = await get_or_404(db, Permission, permission_id, "权限不存在")
    await delete_and_commit(db, permission)
    return Message(message="权限已删除")


# ----------------------------- 审计日志 -----------------------------
@router.get("/audit-logs", response_model=Page[AuditLogOut], summary="操作日志列表")
async def list_audit_logs(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    _: CurrentUser,
    username: str | None = None,
    module: str | None = None,
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if username:
        stmt = stmt.where(AuditLog.username == username)
    if module:
        stmt = stmt.where(AuditLog.module == module)
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


async def _paginate(db: AsyncSession, stmt, params: PageParams):
    from app.api.crud import paginate_query

    return await paginate_query(db, stmt, params.page, params.size)


async def _load_user(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


async def _load_role(db: AsyncSession, role_id: int) -> Role:
    role = await db.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    if role is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return role
