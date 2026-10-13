"""同步内置权限清单，并可选地创建开箱可用的角色模板。

用法：
    .venv/bin/python scripts/seed_permissions.py                 # 只同步权限清单
    .venv/bin/python scripts/seed_permissions.py --with-roles     # 顺带创建角色模板

特性：
* 幂等：权限按编码补齐、角色按名称补齐，已存在的记录不会被覆盖或删除；
* 管理员角色固定绑定内置通配权限 `all`，避免误操作把自己锁在系统外。
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, init_db
from app.core.permissions import ALL_PERMISSION, PERMISSION_CATALOG, sync_permission_catalog
from app.models.system import Permission, Role

ADMIN_ROLE = "管理员"

# 角色模板：名称 → 说明 + 权限编码
ROLE_TEMPLATES: dict[str, tuple[str, tuple[str, ...]]] = {
    "销售员": (
        "负责开单、发货与客户跟进",
        (
            "dashboard:view",
            "customer:view",
            "product:view",
            "sales:view",
            "sales:manage",
            "inventory:view",
            "return:view",
            "report:view",
            "gsp:view",
        ),
    ),
    "采购员": (
        "负责采购下单与到货验收",
        (
            "dashboard:view",
            "supplier:view",
            "product:view",
            "warehouse:view",
            "purchase:view",
            "purchase:manage",
            "inventory:view",
            "report:view",
        ),
    ),
    "仓管员": (
        "负责库存查询、期初建账与出入库核对",
        (
            "dashboard:view",
            "product:view",
            "warehouse:view",
            "inventory:view",
            "inventory:manage",
            "purchase:view",
            "sales:view",
            "report:view",
            "gsp:view",
        ),
    ),
    "财务": (
        "负责收款登记与应收账龄管理",
        (
            "dashboard:view",
            "customer:view",
            "sales:view",
            "finance:view",
            "finance:manage",
            "report:view",
        ),
    ),
    "质量管理": (
        "负责首营资质审核与证照/批次预警处理",
        (
            "dashboard:view",
            "customer:view",
            "supplier:view",
            "product:view",
            "gsp:view",
            "gsp:manage",
            "report:view",
            "inventory:view",
        ),
    ),
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="同步权限清单 / 角色模板")
    parser.add_argument("--with-roles", action="store_true", help="同时创建角色模板")
    args = parser.parse_args()

    await init_db()
    async with AsyncSessionLocal() as db:
        created = await sync_permission_catalog(db)
        print(f"权限清单：新建 {created} 项，共 {len(PERMISSION_CATALOG)} 项登记在案")

        permissions = {
            p.code: p for p in await db.scalars(select(Permission))
        }

        admin_role = await db.scalar(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == ADMIN_ROLE)
        )
        if admin_role is None:
            admin_role = Role(name=ADMIN_ROLE, description="系统管理员")
            db.add(admin_role)
            admin_role.permissions = []
            print(f"角色「{ADMIN_ROLE}」：已创建")
        if ALL_PERMISSION not in {p.code for p in admin_role.permissions}:
            admin_role.permissions.append(permissions[ALL_PERMISSION])
            print(f"角色「{ADMIN_ROLE}」：已补授内置「全部权限」")

        if args.with_roles:
            for name, (description, codes) in ROLE_TEMPLATES.items():
                role = await db.scalar(
                    select(Role)
                    .options(selectinload(Role.permissions))
                    .where(Role.name == name)
                )
                if role is not None:
                    print(f"角色「{name}」：已存在，跳过")
                    continue
                missing = [code for code in codes if code not in permissions]
                if missing:
                    raise SystemExit(f"权限清单缺少编码：{missing}")
                role = Role(name=name, description=description)
                role.permissions = [permissions[code] for code in codes]
                db.add(role)
                print(f"角色「{name}」：已创建（{len(codes)} 项权限）")

        await db.commit()
    print("完成")


if __name__ == "__main__":
    asyncio.run(main())
