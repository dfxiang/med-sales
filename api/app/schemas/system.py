from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    employee_id: int | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=100)
    employee_id: int | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    employee_id: int | None
    is_active: bool
    created_at: datetime
    roles: list["RoleOut"] = []


class MeOut(UserOut):
    """当前登录用户信息：附带扁平化的权限编码，便于前端做菜单/按钮控制。"""

    permissions: list[str] = []
    is_superuser: bool = False


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = None


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    permissions: list["PermissionOut"] = []


class PermissionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=50)
    description: str | None = None


class PermissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    created_at: datetime


class RolePermissionBind(BaseModel):
    permission_ids: list[int] = []


class UserRoleBind(BaseModel):
    role_ids: list[int] = []


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    username: str | None
    action: str
    module: str
    detail: str | None
    ip: str | None
    created_at: datetime


class GetTokenByApiKey(BaseModel):
    api_key: str
    user_id: int


UserOut.model_rebuild()
RoleOut.model_rebuild()
