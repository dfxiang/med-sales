"""初始化/更新管理员账号。

用法：
    .venv/bin/python scripts/create_admin.py --username admin --password admin123
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.core.permissions import ALL_PERMISSION, sync_permission_catalog
from app.core.security import hash_password
from app.models.system import Permission, Role, User, role_permissions, user_roles


async def main() -> None:
    parser = argparse.ArgumentParser(description="创建管理员账号")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    args = parser.parse_args()

    await init_db()
    async with AsyncSessionLocal() as db:
        await sync_permission_catalog(db)
        user = await db.scalar(select(User).where(User.username == args.username))
        if user is None:
            user = User(
                username=args.username,
                password_hash=hash_password(args.password),
                is_active=True,
            )
            db.add(user)
            await db.flush()
            print(f"已创建管理员账号：{args.username}")
        else:
            user.password_hash = hash_password(args.password)
            user.is_active = True
            print(f"已更新管理员账号：{args.username}")

        role = await db.scalar(select(Role).where(Role.name == "管理员"))
        if role is None:
            role = Role(name="管理员", description="系统管理员")
            db.add(role)
            await db.flush()
        permission = await db.scalar(
            select(Permission).where(Permission.code == ALL_PERMISSION)
        )
        if permission is None:  # 正常情况下已由 sync_permission_catalog 建好
            permission = Permission(code=ALL_PERMISSION, name="全部权限")
            db.add(permission)
            await db.flush()

        bound_role = (
            await db.execute(
                select(user_roles.c.user_id).where(user_roles.c.user_id == user.id)
            )
        ).first()
        if bound_role is None:
            await db.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
        bound_perm = (
            await db.execute(
                select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role.id
                )
            )
        ).first()
        if bound_perm is None:
            await db.execute(
                role_permissions.insert().values(role_id=role.id, permission_id=permission.id)
            )
        await db.commit()
    print("完成")


if __name__ == "__main__":
    asyncio.run(main())
