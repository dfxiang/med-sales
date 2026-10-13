from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.crud import create_and_commit, get_or_404, update_and_commit
from app.api.deps import CurrentUser, get_page_params, require_permission
from app.core.database import get_db
from app.core.permissions import ALL_PERMISSION, is_superuser
from app.core.security import hash_password
from app.models.system import (
    AuditLog,
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)
from app.schemas.common import Message, Page, PageParams, page_of
from app.schemas.system import (
    AdminPasswordReset,
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
PROFILE_FIELDS = ("display_name", "phone", "email")

VIEW_USERS = Depends(require_permission("system:user:view"))
MANAGE_USERS = Depends(require_permission("system:user:manage"))
VIEW_ROLES = Depends(require_permission("system:role:view"))
MANAGE_ROLES = Depends(require_permission("system:role:manage"))
VIEW_PERMISSIONS = Depends(require_permission("system:permission:view"))
MANAGE_PERMISSIONS = Depends(require_permission("system:permission:manage"))
VIEW_LOGS = Depends(require_permission("system:log:view"))


async def _audit(db: AsyncSession, current: User, action: str, detail: str) -> None:
    """写一条系统管理审计日志（随业务事务一起提交）。"""
    db.add(
        AuditLog(
            user_id=current.id,
            username=current.username,
            action=action,
            module="system",
            detail=detail[:500],
        )
    )


# ----------------------------- 用户管理 -----------------------------
@router.get(
    "/users",
    response_model=Page[UserOut],
    summary="用户列表",
    dependencies=[VIEW_USERS],
)
async def list_users(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    keyword: str | None = None,
):
    stmt = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .order_by(User.id)
    )
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(User.username.ilike(like) | User.display_name.ilike(like))
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    summary="用户详情",
    dependencies=[VIEW_USERS],
)
async def get_user(user_id: int, db: Db):
    return await _load_user(db, user_id)


@router.post(
    "/users",
    response_model=UserOut,
    status_code=201,
    summary="创建用户",
    dependencies=[MANAGE_USERS],
)
async def create_user(payload: UserCreate, db: Db, current: CurrentUser):
    exists = await db.scalar(select(User).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=(payload.display_name or "").strip() or payload.username,
        phone=payload.phone,
        email=payload.email,
        employee_id=payload.employee_id,
        is_active=payload.is_active,
    )
    user = await create_and_commit(db, user)
    await _audit(db, current, "create", f"创建用户 {user.username}")
    await db.commit()
    return await _load_user(db, user.id)


@router.put(
    "/users/{user_id}",
    response_model=UserOut,
    summary="更新用户",
    dependencies=[MANAGE_USERS],
)
async def update_user(user_id: int, payload: UserUpdate, db: Db, current: CurrentUser):
    user = await _load_user(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    # 资料字段单独处理：这里"显式传空"是有效语义（电话 / 邮箱清空），
    # 不能走 update_and_commit 的"None 视为未修改"规则。
    profile_data = {field: data.pop(field) for field in PROFILE_FIELDS if field in data}
    if "display_name" in profile_data and not (profile_data["display_name"] or "").strip():
        raise HTTPException(status_code=400, detail="显示名称不能为空")
    if data.get("is_active") is False:
        if user.id == current.id:
            raise HTTPException(status_code=400, detail="不能停用当前登录账号")
        if await _is_last_active_superuser(db, user):
            raise HTTPException(status_code=400, detail="系统需保留至少一个可用的管理员账号")
    if data.get("password"):
        data["password_hash"] = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    for field, value in profile_data.items():
        setattr(user, field, value)
    await update_and_commit(db, user, data)
    await _audit(
        db,
        current,
        "update",
        "更新用户 {}（{}）".format(
            user.username,
            ", ".join(sorted(list(data) + list(profile_data))) or "无字段变更",
        ),
    )
    await db.commit()
    return await _load_user(db, user_id)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=Message,
    summary="重置用户登录密码",
    dependencies=[MANAGE_USERS],
)
async def reset_user_password(
    user_id: int, payload: AdminPasswordReset, db: Db, current: CurrentUser
):
    """管理员重置密码：不校验原密码、不做二次确认（见设计文档 §4.4）。

    该能力等价于"账号接管"，因此只对 system:user:manage 开放，并写独立审计 action。
    """
    user = await _load_user(db, user_id)
    user.password_hash = hash_password(payload.new_password)
    await _audit(db, current, "reset_password", f"重置用户 {user.username} 的登录密码")
    await db.commit()
    return Message(message="密码已重置")


@router.delete(
    "/users/{user_id}",
    response_model=Message,
    summary="删除用户",
    dependencies=[MANAGE_USERS],
)
async def delete_user(user_id: int, db: Db, current: CurrentUser):
    user = await _load_user(db, user_id)
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    if await _is_last_active_superuser(db, user):
        raise HTTPException(status_code=400, detail="系统需保留至少一个可用的管理员账号")
    await _audit(db, current, "delete", f"删除用户 {user.username}")
    await db.delete(user)
    await db.commit()
    return Message(message="用户已删除")


@router.post(
    "/users/{user_id}/roles",
    response_model=UserOut,
    summary="为用户分配角色",
    dependencies=[MANAGE_USERS],
)
async def bind_user_roles(user_id: int, payload: UserRoleBind, db: Db, current: CurrentUser):
    user = await _load_user(db, user_id)
    roles: list[Role] = []
    for role_id in payload.role_ids:
        roles.append(await get_or_404(db, Role, role_id, f"角色 {role_id} 不存在"))
    keeps_super = any(ALL_PERMISSION in {p.code for p in role.permissions} for role in roles)
    if user.id == current.id and not keeps_super and await _is_last_active_superuser(db, user):
        raise HTTPException(status_code=400, detail="系统需保留至少一个可用的管理员账号")
    user.roles = roles
    await _audit(
        db,
        current,
        "bind",
        f"设置用户 {user.username} 的角色：{[r.name for r in roles] or '（清空）'}",
    )
    await db.commit()
    return await _load_user(db, user_id)


# ----------------------------- 角色管理 -----------------------------
@router.get(
    "/roles",
    response_model=Page[RoleOut],
    summary="角色列表",
    dependencies=[VIEW_ROLES],
)
async def list_roles(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    keyword: str | None = None,
):
    stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.id)
    if keyword:
        stmt = stmt.where(Role.name.ilike(f"%{keyword}%"))
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get(
    "/roles/{role_id}",
    response_model=RoleOut,
    summary="角色详情",
    dependencies=[VIEW_ROLES],
)
async def get_role(role_id: int, db: Db):
    return await _load_role(db, role_id)


@router.post(
    "/roles",
    response_model=RoleOut,
    status_code=201,
    summary="创建角色",
    dependencies=[MANAGE_ROLES],
)
async def create_role(payload: RoleCreate, db: Db, current: CurrentUser):
    exists = await db.scalar(select(Role).where(Role.name == payload.name))
    if exists:
        raise HTTPException(status_code=400, detail="角色名已存在")
    role = await create_and_commit(db, Role(**payload.model_dump()))
    await _audit(db, current, "create", f"创建角色 {role.name}")
    await db.commit()
    return await _load_role(db, role.id)


@router.put(
    "/roles/{role_id}",
    response_model=RoleOut,
    summary="更新角色",
    dependencies=[MANAGE_ROLES],
)
async def update_role(role_id: int, payload: RoleUpdate, db: Db, current: CurrentUser):
    role = await _load_role(db, role_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("name") and data["name"] != role.name:
        exists = await db.scalar(select(Role).where(Role.name == data["name"]))
        if exists:
            raise HTTPException(status_code=400, detail="角色名已存在")
    await update_and_commit(db, role, data)
    await _audit(db, current, "update", f"更新角色 {role.name}")
    await db.commit()
    return await _load_role(db, role_id)


@router.delete(
    "/roles/{role_id}",
    response_model=Message,
    summary="删除角色",
    dependencies=[MANAGE_ROLES],
)
async def delete_role(role_id: int, db: Db, current: CurrentUser):
    role = await _load_role(db, role_id)
    user_count = (
        await db.scalar(
            select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role_id)
        )
        or 0
    )
    if user_count:
        raise HTTPException(
            status_code=400,
            detail=f"该角色仍分配给 {user_count} 个账号，请先解除关联再删除",
        )
    await _audit(db, current, "delete", f"删除角色 {role.name}")
    await db.delete(role)
    await db.commit()
    return Message(message="角色已删除")


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RoleOut,
    summary="为角色分配权限",
    dependencies=[MANAGE_ROLES],
)
async def bind_role_permissions(
    role_id: int, payload: RolePermissionBind, db: Db, current: CurrentUser
):
    role = await _load_role(db, role_id)
    permissions: list[Permission] = []
    for permission_id in payload.permission_ids:
        permissions.append(
            await get_or_404(db, Permission, permission_id, f"权限 {permission_id} 不存在")
        )
    if ALL_PERMISSION in {p.code for p in role.permissions} and ALL_PERMISSION not in {
        p.code for p in permissions
    }:
        raise HTTPException(
            status_code=400,
            detail="内置「全部权限」不允许从角色上移除，如需降权请改用其他角色",
        )
    role.permissions = permissions
    await _audit(db, current, "bind", f"设置角色 {role.name} 的权限：{len(permissions)} 项")
    await db.commit()
    return await _load_role(db, role_id)


# ----------------------------- 权限管理 -----------------------------
@router.get(
    "/permissions",
    response_model=Page[PermissionOut],
    summary="权限列表",
    dependencies=[VIEW_PERMISSIONS],
)
async def list_permissions(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
    keyword: str | None = None,
):
    stmt = select(Permission).order_by(Permission.id)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            Permission.code.ilike(like)
            | Permission.name.ilike(like)
            | Permission.description.ilike(like)
        )
    rows, total = await _paginate(db, stmt, params)
    return page_of(rows, total, params.page, params.size)


@router.get(
    "/permissions/{permission_id}",
    response_model=PermissionOut,
    summary="权限详情",
    dependencies=[VIEW_PERMISSIONS],
)
async def get_permission(permission_id: int, db: Db):
    return await get_or_404(db, Permission, permission_id, "权限不存在")


@router.post(
    "/permissions",
    response_model=PermissionOut,
    status_code=201,
    summary="创建权限",
    dependencies=[MANAGE_PERMISSIONS],
)
async def create_permission(payload: PermissionCreate, db: Db, current: CurrentUser):
    exists = await db.scalar(select(Permission).where(Permission.code == payload.code))
    if exists:
        raise HTTPException(status_code=400, detail="权限编码已存在")
    permission = await create_and_commit(db, Permission(**payload.model_dump()))
    await _audit(db, current, "create", f"创建权限 {permission.code}（{permission.name}）")
    await db.commit()
    return permission


@router.put(
    "/permissions/{permission_id}",
    response_model=PermissionOut,
    summary="更新权限",
    dependencies=[MANAGE_PERMISSIONS],
)
async def update_permission(
    permission_id: int, payload: PermissionUpdate, db: Db, current: CurrentUser
):
    permission = await get_or_404(db, Permission, permission_id, "权限不存在")
    await update_and_commit(db, permission, payload.model_dump(exclude_unset=True))
    await _audit(db, current, "update", f"更新权限 {permission.code}")
    await db.commit()
    return permission


@router.delete(
    "/permissions/{permission_id}",
    response_model=Message,
    summary="删除权限",
    dependencies=[MANAGE_PERMISSIONS],
)
async def delete_permission(permission_id: int, db: Db, current: CurrentUser):
    permission = await get_or_404(db, Permission, permission_id, "权限不存在")
    if permission.code == ALL_PERMISSION:
        raise HTTPException(status_code=400, detail="内置「全部权限」不允许删除")
    role_count = (
        await db.scalar(
            select(func.count())
            .select_from(role_permissions)
            .where(role_permissions.c.permission_id == permission_id)
        )
        or 0
    )
    if role_count:
        raise HTTPException(
            status_code=400,
            detail=f"该权限仍分配给 {role_count} 个角色，请先解除关联再删除",
        )
    await _audit(db, current, "delete", f"删除权限 {permission.code}（{permission.name}）")
    await db.delete(permission)
    await db.commit()
    return Message(message="权限已删除")


# ----------------------------- 审计日志 -----------------------------
@router.get(
    "/audit-logs",
    response_model=Page[AuditLogOut],
    summary="操作日志列表",
    dependencies=[VIEW_LOGS],
)
async def list_audit_logs(
    db: Db,
    params: Annotated[PageParams, Depends(get_page_params)],
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


async def _is_last_active_superuser(db: AsyncSession, user: User) -> bool:
    """该用户是否为系统中唯一可用的（启用状态）超级权限账号。"""
    if not is_superuser(user):
        return False
    others = (
        await db.scalar(
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(user_roles, user_roles.c.user_id == User.id)
            .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(
                Permission.code == ALL_PERMISSION,
                User.is_active.is_(True),
                User.id != user.id,
            )
        )
        or 0
    )
    return others == 0


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
