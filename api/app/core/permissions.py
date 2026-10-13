"""权限目录与判定逻辑。

约定
----
* 权限编码统一为 `模块:动作` 或 `模块:对象:动作`，例如 `sales:view`、
  `system:user:manage`；模块名即编码的第一段，前端据此分组展示。
* 内置超级权限编码为 `all`（通配），拥有该权限的账号可通过任何权限校验。
  部署脚本 `scripts/create_admin.py` 会把 `all` 绑到「管理员」角色上。
* 权限清单（`PERMISSION_CATALOG`）是系统内置的“能力字典”，由
  `sync_permission_catalog()` 在服务启动时幂等同步进 `permissions` 表：
  只补建缺失项，不修改、不删除既有记录。
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import Permission, User

# 通配权限：拥有它即视为拥有全部权限
ALL_PERMISSION = "all"


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    name: str
    description: str

    @property
    def module(self) -> str:
        return self.code.split(":", 1)[0]


# --------------------------------------------------------------------------
# 权限清单：新增受控接口时，在这里登记编码，并在路由上引用同一编码。
# --------------------------------------------------------------------------
PERMISSION_CATALOG: tuple[PermissionSpec, ...] = (
    PermissionSpec(ALL_PERMISSION, "全部权限", "内置超级权限，通配所有权限，不可删除"),
    # 工作台
    PermissionSpec("dashboard:view", "查看经营看板", "经营看板及首页统计卡片"),
    # 系统管理
    PermissionSpec("system:user:view", "查看用户", "查询用户列表与详情"),
    PermissionSpec("system:user:manage", "维护用户", "新增、编辑、删除用户及分配角色"),
    PermissionSpec("system:role:view", "查看角色", "查询角色列表与详情"),
    PermissionSpec("system:role:manage", "维护角色", "新增、编辑、删除角色及分配权限"),
    PermissionSpec("system:permission:view", "查看权限", "查询权限清单"),
    PermissionSpec("system:permission:manage", "维护权限", "新增、编辑、删除权限"),
    PermissionSpec("system:log:view", "查看操作日志", "查询审计日志"),
    # 组织与员工
    PermissionSpec("org:department:view", "查看部门", "查询部门"),
    PermissionSpec("org:department:manage", "维护部门", "新增、编辑、删除部门"),
    PermissionSpec("org:employee:view", "查看员工", "查询员工档案"),
    PermissionSpec("org:employee:manage", "维护员工", "新增、编辑、删除员工"),
    # 主数据
    PermissionSpec("customer:view", "查看客户", "查询客户档案"),
    PermissionSpec("customer:manage", "维护客户", "新增、编辑、删除客户"),
    PermissionSpec("product:view", "查看商品", "查询商品、分类、厂家与调价历史"),
    PermissionSpec("product:manage", "维护商品", "新增、编辑、删除商品及调价"),
    PermissionSpec("supplier:view", "查看供应商", "查询供应商档案"),
    PermissionSpec("supplier:manage", "维护供应商", "新增、编辑、删除供应商"),
    PermissionSpec("warehouse:view", "查看仓库", "查询仓库"),
    PermissionSpec("warehouse:manage", "维护仓库", "新增、编辑、删除仓库"),
    # 进销存
    PermissionSpec("purchase:view", "查看采购单", "查询采购订单"),
    PermissionSpec("purchase:manage", "维护采购单", "创建、修改、删除采购单及收货入库"),
    PermissionSpec("sales:view", "查看销售订单", "查询销售订单"),
    PermissionSpec("sales:manage", "维护销售订单", "创建、删除销售订单及发货、取消"),
    PermissionSpec("inventory:view", "查看库存", "查询库存与库存流水"),
    PermissionSpec("inventory:manage", "维护库存", "期初建账等库存调整操作"),
    PermissionSpec("return:view", "查看退货单", "查询销售退货单"),
    PermissionSpec("return:manage", "维护退货单", "创建、删除退货单及退货入库"),
    # 财务
    PermissionSpec("finance:view", "查看财务数据", "查询收款记录与应收账龄"),
    PermissionSpec("finance:manage", "维护收款记录", "登记、删除收款记录"),
    # 报表
    PermissionSpec("report:view", "查看报表", "销售/客户/员工/商品/库存等报表"),
    # GSP 合规
    PermissionSpec("gsp:view", "查看 GSP 档案", "查询证照、批次、资质与预警"),
    PermissionSpec("gsp:manage", "维护 GSP 档案", "证照与批次的建档、审核、附件管理"),
)

CATALOG_BY_CODE: dict[str, PermissionSpec] = {spec.code: spec for spec in PERMISSION_CATALOG}


def code_label(code: str) -> str:
    """权限编码 → 中文名称（用于错误提示，未知编码原样返回）。"""
    spec = CATALOG_BY_CODE.get(code)
    return spec.name if spec else code


def permission_codes(user: User) -> set[str]:
    """用户经角色继承到的全部权限编码。"""
    codes: set[str] = set()
    for role in user.roles:
        for permission in role.permissions:
            codes.add(permission.code)
    return codes


def is_superuser(user: User) -> bool:
    return ALL_PERMISSION in permission_codes(user)


def has_permission(user: User, *codes: str) -> bool:
    """是否具备其中任一权限；`all` 通配。"""
    if not codes:
        return True
    owned = permission_codes(user)
    if ALL_PERMISSION in owned:
        return True
    return any(code in owned for code in codes)


async def sync_permission_catalog(db: AsyncSession) -> int:
    """把内置权限清单幂等同步进数据库，返回新建条数。"""
    existing = set(await db.scalars(select(Permission.code)))
    created = 0
    for spec in PERMISSION_CATALOG:
        if spec.code in existing:
            continue
        db.add(Permission(code=spec.code, name=spec.name, description=spec.description))
        created += 1
    if created:
        await db.commit()
    return created
