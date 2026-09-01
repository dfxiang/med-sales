#!/usr/bin/env bash
# 启动 E2E 后端：重置独立的 medsales_e2e 数据库并运行 API（端口 8002）
set -euo pipefail

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_DB="${E2E_DB:-medsales_e2e}"
E2E_PORT="${E2E_PORT:-8002}"

# 确保 E2E 数据库存在（独立于业务库 medsalesdb）
docker exec demo-db psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${E2E_DB}'" | grep -q 1 || \
  docker exec demo-db psql -U postgres -c "CREATE DATABASE ${E2E_DB}"

# 每次运行前重置，保证测试可重复执行
docker exec demo-db psql -U postgres -d "${E2E_DB}" -q -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

export DATABASE_URL="postgresql+asyncpg://postgres:pass01!@127.0.0.1:5688/${E2E_DB}"

cd "${API_DIR}"
"${API_DIR}/.venv/bin/python" scripts/create_admin.py --username admin --password admin123 >/dev/null
exec "${API_DIR}/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port "${E2E_PORT}"
