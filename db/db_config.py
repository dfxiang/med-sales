"""medsalesdb 演示数据库连接配置。

连接参数按以下优先级解析（高 → 低）：

1. 独立环境变量 ``MEDSALESDB_HOST`` / ``MEDSALESDB_PORT`` / ``MEDSALESDB_USER`` /
   ``MEDSALESDB_PASSWORD`` / ``MEDSALESDB_NAME`` / ``MEDSALESDB_ADMIN_DB``；
2. 项目统一变量 ``DATABASE_URL``（与 ``api/.env``、``docker-compose.yml`` 一致），
   例如 ``postgresql+asyncpg://postgres:pass01!@127.0.0.1:5688/medsalesdb``；
3. 内置默认值：``demo-db`` 容器映射到宿主机的 ``127.0.0.1:5688``。

默认连接的目标就是本项目使用的演示库：容器 ``demo-db``（PostgreSQL 17）中的
``medsalesdb``。

在 Docker 网络内执行时，主机名换成容器名即可（容器内部端口是 5432）：

    MEDSALESDB_HOST=demo-db MEDSALESDB_PORT=5432 python run_all.py
"""

import os
from urllib.parse import unquote, urlsplit

# demo-db 容器（docker run -p 5688:5432）在宿主机上的连接参数
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5688
DEFAULT_USER = "postgres"
DEFAULT_PASSWORD = "pass01!"
DEFAULT_NAME = "medsalesdb"


def _from_database_url(url: str) -> dict:
    """解析项目统一的 DATABASE_URL（兼容 postgresql:// 与 postgresql+asyncpg://）。"""
    if not url.startswith(("postgresql://", "postgres://", "postgresql+")):
        raise ValueError(
            f"DATABASE_URL 仅支持 PostgreSQL 连接串（如 postgresql+asyncpg://...），当前为 {url!r}"
        )
    scheme, _, rest = url.partition("://")
    parsed = urlsplit(f"{scheme.split('+', 1)[0]}://{rest}")
    if not parsed.hostname:
        raise ValueError(f"DATABASE_URL 缺少主机名：{url!r}")
    return {
        "host": parsed.hostname,
        "port": parsed.port or DEFAULT_PORT,
        "user": unquote(parsed.username) if parsed.username else DEFAULT_USER,
        "password": unquote(parsed.password) if parsed.password else DEFAULT_PASSWORD,
        "name": unquote(parsed.path.lstrip("/")) or DEFAULT_NAME,
    }


_URL_DEFAULTS = _from_database_url(os.environ["DATABASE_URL"]) if os.environ.get("DATABASE_URL") else {}

DB_HOST = os.environ.get("MEDSALESDB_HOST") or _URL_DEFAULTS.get("host") or DEFAULT_HOST
DB_PORT = int(os.environ.get("MEDSALESDB_PORT") or _URL_DEFAULTS.get("port") or DEFAULT_PORT)
DB_USER = os.environ.get("MEDSALESDB_USER") or _URL_DEFAULTS.get("user") or DEFAULT_USER
DB_PASSWORD = os.environ.get("MEDSALESDB_PASSWORD") or _URL_DEFAULTS.get("password") or DEFAULT_PASSWORD
DB_NAME = os.environ.get("MEDSALESDB_NAME") or _URL_DEFAULTS.get("name") or DEFAULT_NAME

# 用于建库/删库的管理库，默认连到 postgres
ADMIN_DB_NAME = os.environ.get("MEDSALESDB_ADMIN_DB", "postgres")


def conninfo(dbname: str = DB_NAME) -> str:
    """返回 psycopg 使用的连接信息字符串。"""
    return (
        f"host={DB_HOST} port={DB_PORT} dbname={dbname} "
        f"user={DB_USER} password={DB_PASSWORD} client_encoding=UTF8"
    )


def target() -> str:
    """返回可读的连接目标，形如 postgres@127.0.0.1:5688/medsalesdb。"""
    return f"{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
