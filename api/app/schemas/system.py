from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# 联系方式用轻量正则校验：目标只是"别把明显写错的内容存进去"，
# 不引入 email-validator 依赖（见 docs/用户资料扩展设计.md §4.5）。
PHONE_RE = re.compile(r"^[0-9+\-() ]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ProfileFields(BaseModel):
    """资料字段（管理侧与自助侧共用）：显示名称 / 电话 / 邮箱。"""

    display_name: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=100)

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, value: str | None) -> str | None:
        # 注意：空白串保留为空串，由路由决定语义（建号取用户名 / 更新报错）
        return None if value is None else value.strip()

    @field_validator("phone", "email")
    @classmethod
    def _normalize_contact(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:  # 空串 = 清空该字段
            return None
        if info.field_name == "phone" and not PHONE_RE.match(cleaned):
            raise ValueError("电话号码格式不正确（允许数字、+、-、空格、括号）")
        if info.field_name == "email" and not EMAIL_RE.match(cleaned):
            raise ValueError("电子邮箱格式不正确")
        return cleaned


class UserCreate(ProfileFields):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    employee_id: int | None = None
    is_active: bool = True


class UserUpdate(ProfileFields):
    password: str | None = Field(default=None, min_length=6, max_length=100)
    employee_id: int | None = None
    is_active: bool | None = None


class UserOut(ProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    employee_id: int | None
    is_active: bool
    created_at: datetime
    # 只读派生字段：由 User.avatar_url 属性计算（未设置头像时回落默认头像）
    avatar_url: str
    roles: list["RoleOut"] = []


class MeOut(UserOut):
    """当前登录用户信息：附带扁平化的权限编码，便于前端做菜单/按钮控制。"""

    permissions: list[str] = []
    is_superuser: bool = False


class ProfileUpdate(ProfileFields):
    """自助资料更新：只包含用户本人可改的字段（除用户名外的资料）。"""


class PasswordChange(BaseModel):
    """自助改密：必须校验原密码，且新密码两次输入一致。"""

    old_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=6, max_length=100)
    confirm_password: str = Field(min_length=6, max_length=100)


class AdminPasswordReset(BaseModel):
    """管理员重置密码：只填一次新密码，不校验原密码、不做二次确认。"""

    new_password: str = Field(min_length=6, max_length=100)


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
