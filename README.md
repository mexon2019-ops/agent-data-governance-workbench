# Agent 数据治理工作台

V0.3：在 V0.2 八个工作台模块基础上，增加四类关系型数据库元数据采集、元数据目录和字段详情。

## 页面
1. 治理总览
2. 数据源管理（配置、连接测试、手动采集元数据）
3. 数据资产
4. 元数据目录（Schema、表/视图、字段详情）
5. 数据标准
6. 数据质量
7. 治理任务
8. Agent 助手（当前仍为待接入模型的交互骨架）

## 技术栈
- 前端：React + TypeScript + Vite
- 后端：FastAPI + SQLAlchemy 2
- 工作台元数据库：PostgreSQL 16
- 源数据库驱动：SQL Server（pymssql）、Oracle（python-oracledb Thin mode）、MySQL（PyMySQL）、PostgreSQL（psycopg）
- 元数据采集：SQLAlchemy Inspector
- 部署：Docker Compose + Nginx

## 启动
复制 .env.example 为 .env，设置强随机的 POSTGRES_PASSWORD，并按需配置源数据库密码环境变量：

```bash
cp .env.example .env
docker compose up -d --build
```

访问 http://localhost:8080；API 文档 http://localhost:8000/docs。

## 数据源凭据
数据源记录只保存密码环境变量名，不保存源数据库明文密码。Compose 已将以下变量传入后端容器：
- MES_DB_PASSWORD
- ORACLE_DB_PASSWORD
- MYSQL_DB_PASSWORD
- PG_DB_PASSWORD

真实密码只放在服务器受控 .env 或 Docker secrets 中。不要提交真实 .env。源数据库请使用最小权限只读账号。

## V0.3 元数据采集
在“数据源管理”新增数据源并测试连接，随后点击“采集元数据”。采集器只读取系统目录/数据字典，采集 Schema、表/视图、字段、类型、可空、默认值、主外键及注释，不读取业务表数据行。采集结果进入工作台 PostgreSQL，在“元数据目录”中检索并查看字段详情。

API：
- GET /api/v1/metadata/tables
- GET /api/v1/metadata/tables/{table_id}
- POST /api/v1/datasources/{source_id}/sync
- GET /api/v1/datasources/{source_id}/sync-runs

详细设计和验收标准见 docs/V0.3-metadata-ingestion.md。

## OpenMetadata 集成策略
V0.3 先交付轻量元数据采集闭环；OpenMetadata 保留为下一阶段的增强治理引擎，用于扩展统一元数据服务、血缘、治理工作流和更多连接器。官方连接器支持 PostgreSQL、MySQL、Oracle、SQL Server。生产部署需单独评估数据库、搜索引擎和 Ingestion 服务的资源与运维成本，不直接把 Quickstart 组件未经评估地并入企业生产环境。

## 当前边界
- 已有数据源配置、连接测试和元数据采集 API。
- 数据资产、标准、质量和任务页面仍以基础记录管理为主，尚未形成完整治理流程。
- Agent 尚未接入 LangGraph 或外部模型；当前不会将提示词发送给第三方。
- 当前尚无完整登录、RBAC、审批、审计、字段级脱敏和生产级密钥托管；不得直接暴露公网或直接用于生产数据治理。
- 四种源数据库的驱动依赖、网络、TLS、Oracle service name/SID、SQL Server 实例及权限仍需在目标内网环境做真实联调。

## MySQL 测试库（可选）

仓库提供一个隔离的 MySQL 8.0 测试库，包含虚构的 LED 封装制造场景数据结构：生产线、物料、设备、生产订单、质量检验、不良记录，以及一个视图。所有样例数据均为虚构，不包含企业真实数据。

### 启动

先复制并编辑环境变量文件，至少修改 PostgreSQL、MySQL root 和只读账号密码：

```bash
cp .env.example .env
```

启动测试 MySQL：

```bash
docker compose --profile mysql-test up -d mysql-test
docker compose ps
docker compose logs -f mysql-test
```

MySQL 仅绑定宿主机回环地址 `127.0.0.1:3307`，不会默认暴露到局域网。若工作台后端也运行在同一 Docker Compose 网络中，数据源连接应填写：

| 配置 | 值 |
|---|---|
| 类型 | MySQL |
| 主机 | mysql-test |
| 端口 | 3306 |
| 数据库 | mes_test |
| 用户 | metadata_reader |
| 密码环境变量名 | MYSQL_TEST_READER_PASSWORD |

在工作台“数据源管理”创建数据源，密码环境变量名填 `MYSQL_TEST_READER_PASSWORD`，然后测试连接并采集元数据。

如果从宿主机上的数据库客户端连接，使用 `127.0.0.1:3307`，用户名 `metadata_reader` 和 `.env` 中配置的只读密码。

### 测试账号权限

初始化脚本创建 `metadata_reader`，仅授予 `mes_test.*` 上的 `SELECT`、`SHOW VIEW` 权限。采集程序只调用元数据 Inspector，不读取业务表数据行。不要把此测试容器改成生产数据库，也不要将端口改为公网或不受控网段可访问。

### 重置测试库

以下操作会删除该测试 MySQL 的 Docker 数据卷及其中所有测试数据，请确认只用于本测试库：

```bash
docker compose --profile mysql-test down
docker volume rm agent-data-governance-workbench_mysqltestdata
docker compose --profile mysql-test up -d mysql-test
```

如项目目录名不同，实际卷名可能不同，可先用 `docker volume ls` 确认。真实密码只保存在本机 `.env`，不要提交到 Git。
