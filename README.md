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
│   └── API接口文档.md        # 119 个接口的中文接口文档（自动生成）
├── api/                     # 后端（FastAPI，全异步）
│   ├── app/                 # 应用源码（模型/路由/校验/核心）
│   ├── tests/               # 接口测试（58 个用例）
│   ├── scripts/             # 初始化管理员、生成接口文档脚本
│   ├── Dockerfile           # 容器镜像
│   ├── docker-compose.yml   # 一键容器化部署
│   └── README.md            # 后端使用说明
├── frontend/                # 前端（Vue 3，已实现全部页面）
│   ├── Dockerfile           # 前端容器镜像（nginx 托管 + API 反代）
│   ├── nginx.conf           # 静态资源 + /api 反代配置
│   ├── tests/e2e/           # Playwright WebUI 测试（39 个用例）
│   └── README.md            # 前端技术栈、页面规划、路由与对接约定
├── db/                      # 演示数据库 medsalesdb 的建库与造数脚本
│   ├── schema.sql           # 18 张业务表 + 7 个视图的 DDL（含中文注释）
│   ├── mock_params.py       # 数据规模/区间/年度目标等生成参数
│   ├── create_database.py   # 建库并执行 schema.sql
│   ├── generate_mock_data.py# 生成四年半 mock 数据
│   ├── verify_database.py   # 校验结构、规模与关键指标
│   ├── run_all.py           # 一键执行以上三步
│   └── README.md            # 连接参数、运行方式、数据模型与规模说明
├── docker-compose.yml       # 前后端一体化容器编排
└── .gitignore
```

---

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 认证 | 用户登录（JWT）、系统对接（API Key 换取令牌）、个人资料 / 头像 / 自助改密（右上角） |
| 系统管理 | 用户（显示名称 / 电话 / 邮箱 / 头像）、角色、权限、操作日志、管理员重置密码 |
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
| GSP 合规 | 首营资质档案（证照审核 + 扫描件归档）、交易准入校验、到期预警中心、批次批号与效期管理 |

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

建库与造数脚本位于 [db/](db/README.md)：`schema.sql` 定义 18 张业务表与 7 个视图，
`generate_mock_data.py` 按 `mock_params.py` 的参数生成四年半演示数据，
`verify_database.py` 校验结构与销售/毛利/库存口径。

详细结构见 [docs/数据库结构分析.md](docs/数据库结构分析.md)。

---

## 快速开始

### 演示数据（medsalesdb）

如果本机还没有 `medsalesdb`（或想重建一套演示数据），用 [db/](db/README.md) 下的脚本一键完成
建库 + 造数 + 校验（约 2 分钟，默认生成 2022-01-01 ~ 2026-07-31 共四年半数据）：

```bash
cd db
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 依赖仅 psycopg
.venv/bin/python run_all.py            # 数据库不存在时创建并初始化
.venv/bin/python run_all.py --reset    # 删除已有 medsalesdb 后重建
```

默认连接本项目的 `demo-db` 容器（`127.0.0.1:5688`），也可直接用 `DATABASE_URL`
或 `MEDSALESDB_*` 环境变量指向其它实例。详细参数见 [db/README.md](db/README.md)。

> 报表走预聚合汇总表（[docs/销售报表汇总表.md](docs/销售报表汇总表.md)），造数脚本
> 直接写明细表，因此生成数据后要再回填一次，否则报表会全为 0：
> `cd api && .venv/bin/python scripts/rebuild_sales_rollup.py`

### 后端（本地）

```bash
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # 按实际数据库连接修改
.venv/bin/python scripts/create_admin.py --username admin --password admin123
.venv/bin/python scripts/seed_permissions.py --with-roles   # 可选：内置角色模板（销售员/仓管员/财务…）
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 后端（Docker）

```bash
cd api
SYS_API_KEYS=你的对接key docker compose up -d --build
```

服务地址：`http://127.0.0.1:8001`，Swagger 文档：`http://127.0.0.1:8001/docs`

### 前后端一体化（Docker Compose，推荐）

在仓库根目录一键启动前端 + 后端：

```bash
SYS_API_KEYS=你的对接key docker compose up -d --build
```

- 前端 Web：http://127.0.0.1:8088（nginx 托管，`/api` 自动反代到后端）
- 后端 API：http://127.0.0.1:8001，Swagger：http://127.0.0.1:8001/docs
- 对象存储 MinIO：S3 API http://127.0.0.1:9020，控制台 http://127.0.0.1:9021（见下方「对象存储」）

局域网内其他电脑可通过宿主机局域网 IP 访问前端，例如 `http://192.168.20.191:8088`（端口已绑定 `0.0.0.0`；若无法访问请放行宿主机防火墙 8088/8001 端口）。

停止：

```bash
docker compose down
```

### 对象存储（本系统专用 MinIO）

系统自带一套**专用的** MinIO（与 kb / biz-oa / datahive 的 MinIO 相互独立），用于 GSP 证照扫描件等合规文件归档。证照扫描件在「证照管理 → 扫描件」或「资质档案」中上传，换证时旧版本自动留档。随 `docker compose up` 一并启动：

| 项目 | 值 |
| --- | --- |
| 服务名 | `medsales-minio` |
| S3 API | `http://127.0.0.1:9020` |
| 控制台 | `http://127.0.0.1:9021` |
| 默认账号 | `medsales` / `medsales-minio-secret`（生产环境请通过 `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` 覆盖） |
| Bucket | `medsales`（由 `medsales-minio-init` 一次性创建，私有读写） |
| 数据卷 | `medsales-minio-data` |

后端通过环境变量 `S3_ENDPOINT_URL / S3_ACCESS_KEY / S3_SECRET_KEY / S3_BUCKET / S3_REGION` 连接（见 `docker-compose.yml`）。

### 初始管理员账号

| 项目 | 值 |
| --- | --- |
| 用户名 | admin |
| 密码 | admin123 |

> 该账号存储在业务库 `medsalesdb` 的 `users` 表中（启动时通过 `scripts/create_admin.py` 初始化）。**首次登录后请及时修改默认密码**：
>
> ```bash
> # 在 api 目录下执行（需设置正确的 DATABASE_URL）
> .venv/bin/python scripts/create_admin.py --username admin --password 你的新密码
> ```
> 也可以自助修改：登录后点右上角头像 → 「修改密码」（需填原密码 + 确认新密码）；
> 管理员也可在系统管理 → 用户管理页面用「重置密码」直接为该账号设置新密码。

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
| [API接口文档](docs/API接口文档.md) | 全部接口的中文规范文档（119 个接口） |
| [GSP 合规闭环](docs/GSP合规闭环.md) | 首营资质建档/审核、交易准入校验、到期预警、换证归档的设计与验证 |
| [权限控制说明](docs/权限控制说明.md) | 权限模型、编码约定、内置约束、扩展步骤与验证方法 |
| [销售报表汇总表](docs/销售报表汇总表.md) | 报表预聚合表结构、按键重算的维护时序、回填与对账、优化前后实测 |
| [缺陷清单](docs/缺陷清单.md) | 对照运行环境的逐项排查记录与修复验证 |
| [演示数据库初始化](db/README.md) | medsalesdb 建库/造数脚本、连接参数、可调生成参数与数据规模 |
| [后端说明](api/README.md) | 后端部署、配置、测试、容器化 |
| [前端说明](frontend/README.md) | 前端技术栈、页面实现、测试与部署方式 |

---

## 路线图

- [x] 数据库结构分析
- [x] 系统功能清单
- [x] 后端 API（全异步，含测试与容器化）
- [x] 中文接口文档
- [x] 前端脚手架与全部页面开发（Playwright 39 个用例通过）
- [x] 前后端容器化部署（docker compose 一键启动）
- [x] 演示数据建库/造数/校验脚本入库（db/，参数集中可调）
- [x] 权限控制闭环：接口级强校验 + 角色/权限管理 + 菜单与按钮联动（见 [权限控制说明](docs/权限控制说明.md)）
- [ ] 数据权限（按区域/部门做行级过滤）、CI/CD 流水线
