"""创建 medsalesdb 数据库并执行 schema.sql（建表、建索引、建视图、加注释）。

默认连接本项目的 `demo-db` 容器（127.0.0.1:5688），可用 MEDSALESDB_*
或项目统一的 DATABASE_URL 覆盖，详见 db_config.py。

用法：
    python create_database.py            # 数据库不存在时创建并初始化
    python create_database.py --reset    # 删除已有 medsalesdb 后重建

注意：--reset 只重建 schema.sql 中的 18 张业务表与 7 个视图；用户/角色/证照等
系统表由 API 服务启动时自动补建，重建后需重新执行 api/scripts/create_admin.py。
"""

import argparse
import sys
from pathlib import Path

import psycopg

from db_config import ADMIN_DB_NAME, DB_NAME, conninfo, target

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_SQL_PATH = BASE_DIR / "schema.sql"


def database_exists(conn: psycopg.Connection, dbname: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
    ).fetchone()
    return row is not None


def drop_database(conn: psycopg.Connection, dbname: str) -> None:
    """断开目标库连接并删除数据库。"""
    conn.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid()
        """,
        (dbname,),
    )
    conn.execute(f'DROP DATABASE IF EXISTS "{dbname}"')


def create_database(reset: bool = False) -> None:
    print(f"[create_database] 目标连接：{target()}")
    # 1) 连接管理库，创建/重建 medsalesdb
    with psycopg.connect(conninfo(ADMIN_DB_NAME), autocommit=True) as conn:
        exists = database_exists(conn, DB_NAME)
        if exists and not reset:
            print(f"[create_database] 数据库 {DB_NAME} 已存在，跳过创建（如需重建请加 --reset）")
        else:
            if exists:
                print(f"[create_database] 删除已有数据库 {DB_NAME} ...")
                drop_database(conn, DB_NAME)
            print(f"[create_database] 创建数据库 {DB_NAME} (UTF8) ...")
            conn.execute(f'CREATE DATABASE "{DB_NAME}" ENCODING \'UTF8\'')

    # 2) 连接 medsalesdb，执行 DDL
    schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    with psycopg.connect(conninfo(DB_NAME), autocommit=True) as conn:
        print("[create_database] 执行 schema.sql（建表/索引/视图/注释）...")
        conn.execute(schema_sql)

    # 3) 汇总对象数量
    with psycopg.connect(conninfo(DB_NAME), autocommit=True) as conn:
        table_count = conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
        ).fetchone()[0]
        view_count = conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='VIEW'"
        ).fetchone()[0]
        index_count = conn.execute(
            "SELECT count(*) FROM pg_indexes WHERE schemaname='public'"
        ).fetchone()[0]
        table_comment_count = conn.execute(
            "SELECT count(*) FROM pg_description d JOIN pg_class c ON c.oid=d.objoid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relkind IN ('r','v') AND d.objsubid=0"
        ).fetchone()[0]
        column_comment_count = conn.execute(
            "SELECT count(*) FROM pg_description d JOIN pg_class c ON c.oid=d.objoid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND d.objsubid > 0"
        ).fetchone()[0]

    print(f"[create_database] 完成：数据库 {DB_NAME}，"
          f"表 {table_count} 张，视图 {view_count} 个，索引 {index_count} 个，"
          f"对象注释 {table_comment_count} 条，列注释 {column_comment_count} 条")


def main() -> None:
    parser = argparse.ArgumentParser(description="创建并初始化 medsalesdb 数据库")
    parser.add_argument("--reset", action="store_true", help="删除已有 medsalesdb 后重建")
    args = parser.parse_args()
    try:
        create_database(reset=args.reset)
    except Exception as exc:  # noqa: BLE001
        print(f"[create_database] 失败：{exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
