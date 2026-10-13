#!/usr/bin/env bash
# 启动 E2E 后端：在项目自带的 PostgreSQL 容器里重置独立的 medsales_e2e 库，并运行 API（端口 8002）
#
# 依赖：仓库根目录执行过 `docker compose up -d medsales-db`。
# 容器名与端口默认与 compose 一致，可用环境变量覆盖：
#   E2E_DB_CONTAINER / E2E_DB_PORT / E2E_DB_USER / E2E_DB_PASSWORD / E2E_DB / E2E_PORT
set -euo pipefail

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_DB="${E2E_DB:-medsales_e2e}"
E2E_PORT="${E2E_PORT:-8002}"
E2E_DB_CONTAINER="${E2E_DB_CONTAINER:-medsales-db}"
E2E_DB_USER="${E2E_DB_USER:-postgres}"
E2E_DB_PASSWORD="${E2E_DB_PASSWORD:-pass01!}"

if ! docker ps --format '{{.Names}}' | grep -qx "${E2E_DB_CONTAINER}"; then
  echo "找不到数据库容器 ${E2E_DB_CONTAINER}；请先在仓库根目录执行：docker compose up -d medsales-db" >&2
  exit 1
fi

# 宿主机端口：优先用显式传参，否则从容器映射推导（compose 支持用 MEDSALES_DB_PORT 自定义）
if [[ -z "${E2E_DB_PORT:-}" ]]; then
  E2E_DB_PORT="$(docker port "${E2E_DB_CONTAINER}" 5432 2>/dev/null | head -1 | sed 's/.*://')"
fi
E2E_DB_PORT="${E2E_DB_PORT:-5688}"

psql_e2e() { docker exec "${E2E_DB_CONTAINER}" psql -U "${E2E_DB_USER}" "$@"; }

# 确保 E2E 数据库存在（独立于业务库 medsalesdb）
psql_e2e -tAc "SELECT 1 FROM pg_database WHERE datname='${E2E_DB}'" | grep -q 1 || \
  psql_e2e -c "CREATE DATABASE ${E2E_DB}"

# 每次运行前重置，保证测试可重复执行
psql_e2e -d "${E2E_DB}" -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

export DATABASE_URL="postgresql+asyncpg://${E2E_DB_USER}:${E2E_DB_PASSWORD}@127.0.0.1:${E2E_DB_PORT}/${E2E_DB}"

cd "${API_DIR}"
"${API_DIR}/.venv/bin/python" scripts/create_admin.py --username admin --password admin123 >/dev/null
exec "${API_DIR}/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "${E2E_PORT}"
