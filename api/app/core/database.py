from collections.abc import AsyncGenerator

from sqlalchemy import BigInteger, Integer
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


# PostgreSQL 使用 BIGINT，SQLite 降级为 INTEGER 以保证自增主键可用
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 增量字段迁移：(表名, 列名, 列定义)
# create_all 只会补建缺失的表，不会给已有表加列；存量库需要这些 ALTER 才能升级。
_COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("certificates", "review_status", "VARCHAR(20) NOT NULL DEFAULT '待审核'"),
    ("certificates", "reviewed_by", "INTEGER"),
    ("certificates", "reviewed_at", "TIMESTAMP"),
    ("certificates", "review_remark", "VARCHAR(200)"),
    ("certificate_attachments", "version", "INTEGER NOT NULL DEFAULT 1"),
    ("certificate_attachments", "is_current", "BOOLEAN NOT NULL DEFAULT TRUE"),
)


def _sync_migrate_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())
    for table, column, ddl in _COLUMN_MIGRATIONS:
        if table not in tables:
            continue
        if column in {c["name"] for c in inspector.get_columns(table)}:
            continue
        sync_conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供一个异步数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """启动时创建缺失的表（已有表不受影响，新系统表会被补建）。"""
    from app import models  # noqa: F401  确保模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sync_migrate_columns)
