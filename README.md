# 医药销售管理系统（med-sales）

面向**药品、疫苗、医疗器械销售公司**的销售业务管理系统，覆盖客户、商品、采购、销售、库存、退货、财务、报表与 GSP 合规等完整业务链路。

系统后端基于存量业务数据库（`medsalesdb`）逆向重建：数据库中原有 18 张业务表和 7 个报表视图，项目在保留原表结构的基础上补齐了用户权限、批次效期、证照管理等能力，并提供全异步 API 与规划中的前端项目。

---

## 仓库结构

```
med-sales/
├── docs/                    # 项目文档
│   ├── 数据库结构分析.md     # 数据库 18 表 + 7 视图的完整分析
│   ├── 系统功能清单.md       # 13 大模块、约 100 个功能点清单
│   └── API接口文档.md        # 114 个接口的中文接口文档（自动生成）
├── api/                     # 后端（FastAPI，全异步）
│   ├── app/                 # 应用源码（模型/路由/校验/核心）
│   ├── tests/               # 接口测试（53 个用例）
│   ├── scripts/             # 初始化管理员、生成接口文档脚本
│   ├── Dockerfile           # 容器镜像
│   ├── docker-compose.yml   # 一键容器化部署
│   └── README.md            # 后端使用说明
├── frontend/                # 前端（规划中）
│   └── README.md            # 前端技术栈、页面规划、路由与对接约定
└── .gitignore
```

---

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 认证 | 用户登录（JWT）、系统对接（API Key 换取令牌） |
| 系统管理 | 用户、角色、权限、操作日志 |
| 组织与员工 | 部门、员工档案 |
| 客户管理 | 客户档案、类型/等级、信用额度、状态 |
| 商品管理 | 商品、分类、生产厂家、价格调整历史 |
| 供应商管理 | 供应商档案、结算账期、合作状态 |
| 仓库管理 | 全国仓库档案、冷链能力 |
| 采购管理 | 采购订单、到货登记（支持部分收货）、采购入库 |
| 销售管理 | 销售订单、自动计价、库存校验、发货出库、取消 |
| 库存管理 | 库存查询（预警状态）、期初建账、全量流水追溯 |
| 退货管理 | 退货单、退货原因、处理入库 |
| 财务收款 | 收款登记、订单核销、应收账龄分析 |
| 报表分析 | 日/月销售、客户/销售员/商品汇总、订单明细、经营看板 |
| GSP 合规 | 证照管理与到期预警、批次批号与效期管理 |

---

## 技术栈

**后端（api/）**

- Python 3.12 + FastAPI + SQLAlchemy 2.0（全异步）
- PostgreSQL 17（asyncpg）/ 测试用 SQLite（aiosqlite）
- JWT 认证（PBKDF2-SHA256 密码哈希）
- pytest + httpx 接口测试
- Docker / Docker Compose 部署

**前端（frontend/，规划中）**

- Vue 3 + TypeScript + Vite + Element Plus + Pinia + ECharts
- 详见 [frontend/README.md](frontend/README.md)

---

## 数据库

系统运行在 PostgreSQL 容器（`demo-db`）的 `medsalesdb` 数据库上：

- 存量业务表 18 张：客户、商品、供应商、仓库、采购、销售、库存、退货、收款等；
- 存量报表视图 7 个：日/月销售、客户/销售员/商品汇总、订单明细、库存状态；
- 新增系统表 8 张：用户、角色、权限、关联表、审计日志、批次、证照（启动时自动补齐，不改动存量表）；
- 数据规模：4 年半经营数据，单据流水约 490 万条。

详细结构见 [docs/数据库结构分析.md](docs/数据库结构分析.md)。

---

## 快速开始

### 后端（本地）

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # 按实际数据库连接修改
.venv/bin/python scripts/create_admin.py --username admin --password admin123
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 后端（Docker）

```bash
cd api
SYS_API_KEYS=你的对接key docker compose up -d --build
```

服务地址：`http://127.0.0.1:8001`，Swagger 文档：`http://127.0.0.1:8001/docs`

### 测试

```bash
cd api
.venv/bin/python -m pytest -q
```

---

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [数据库结构分析](docs/数据库结构分析.md) | 数据库全貌、表结构、业务规则推断 |
| [系统功能清单](docs/系统功能清单.md) | 功能模块与功能点、实施分期建议 |
| [API接口文档](docs/API接口文档.md) | 全部接口的中文规范文档（114 个接口） |
| [后端说明](api/README.md) | 后端部署、配置、测试、容器化 |
| [前端规划](frontend/README.md) | 前端技术栈、页面与路由规划、对接约定 |

---

## 路线图

- [x] 数据库结构分析
- [x] 系统功能清单
- [x] 后端 API（全异步，含测试与容器化）
- [x] 中文接口文档
- [ ] 前端脚手架与页面开发（规划见 [frontend/README.md](frontend/README.md)）
- [ ] 前后端联调与生产部署
