from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


async def get_or_404(db: AsyncSession, model, obj_id: int, detail: str = "记录不存在") -> object:
    obj = await db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return obj


async def create_and_commit(db: AsyncSession, obj) -> object:
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_and_commit(db: AsyncSession, obj, data: dict) -> object:
    for key, value in data.items():
        if value is not None:
            setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_and_commit(db: AsyncSession, obj) -> None:
    await db.delete(obj)
    await db.commit()


async def paginate_query(
    db: AsyncSession,
    stmt: Select,
    page: int,
    size: int,
) -> tuple[list, int]:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = await db.scalar(count_stmt) or 0
    rows = await db.scalars(stmt.offset((page - 1) * size).limit(size))
    return list(rows.all()), total


async def list_query(
    db: AsyncSession,
    stmt: Select,
    page: int,
    size: int,
) -> tuple[list, int]:
    return await paginate_query(db, stmt, page, size)
