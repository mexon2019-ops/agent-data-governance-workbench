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
8. Agent 助手（本地治理建议 + 可选 OpenAI-compatible 模型网关，基础脱敏、只读上下文）

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

## 产品方向与 V1.0 路线

本项目正式定位为**企业级数据治理平台，以数据治理为核心，Agent 作为智能辅助能力**。建设顺序为：数据源接入与资产目录 -> 数据标准 -> 数据质量 -> 治理整改闭环 -> Agent 智能辅助 -> 分类分级与血缘 -> FineReport/经营分析扩展。

产品架构、安全基线、核心对象、验收范围和迭代计划见 [V1.0 产品架构与建设计划](docs/PRODUCT-ARCHITECTURE-V1.0.md)。

V1.0 优先交付 P0：四类数据库接入、元数据目录、数据标准、只读质量检测、治理任务闭环、基础认证/RBAC/审计和治理驾驶舱。Agent 仅提供可解释、可审计的建议，不直接执行源数据库写操作。

## 工程基础与数据库迁移

后端数据库结构使用 Alembic 管理。Docker backend 容器启动时先执行 `alembic upgrade head`，再启动 API；FastAPI 不再在启动时自动创建/修改表结构。后续数据库模型变更必须提交新的迁移版本。

可通过 `CORS_ALLOWED_ORIGINS` 配置允许访问 API 的前端来源，多个来源用逗号分隔。内网部署请替换为实际 HTTPS 域名。

工程基础实施和旧数据库接管注意事项见 [Sprint 0 工程基础建设](docs/SPRINT-0-ENGINEERING-FOUNDATION.md)。

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

## Sprint 9：元数据结构血缘

元数据采集会读取数据库外键约束并建立字段级结构关联，工作台新增“数据血缘”只读页面。当前仅覆盖数据库声明的外键关系，不代表 ETL、API、FineReport 报表等完整数据流向。详见 [Sprint 9 元数据结构血缘](docs/SPRINT-9-METADATA-LINEAGE.md)。

## Sprint 7：字段级分类分级

元数据字段详情支持敏感级别人工确认，提供基于字段名称的规则建议，并记录分类依据、确认人和时间。建议规则不读取源数据库业务数据行；Agent 仅接收未分级字段数、敏感字段数等聚合统计，不接收字段名称或明细。详见 [Sprint 7 字段分类分级](docs/SPRINT-7-FIELD-CLASSIFICATION.md)。

## Sprint 6：安全治理 Agent
Agent 已接入本地治理建议服务和可选 OpenAI-compatible 模型网关。模型上下文只包含治理汇总计数，用户问题在外发前执行基础脱敏；Agent 只需要 governance:read，不读取源数据库业务明细，也不具备自动执行治理写操作的能力。未配置模型时自动使用本地规则建议。

模型网关配置项：LLM_API_BASE_URL、LLM_API_KEY、LLM_MODEL、LLM_TIMEOUT_SECONDS。外部调用默认关闭，需服务器设置 LLM_EXTERNAL_ENABLED=true，并由用户每次提问时明确勾选外发确认。密钥只保存在服务器 .env 或 Docker secrets，不能提交仓库或暴露给前端。详见 [Sprint 8 外部模型双重授权](docs/SPRINT-8-LLM-OUTBOUND-CONSENT.md)。

详细配置、安全边界和验收标准见 [Sprint 6 安全治理 Agent](docs/SPRINT-6-SAFE-GOVERNANCE-AGENT.md)。基础脱敏不等同于完整 DLP；生产环境启用外部模型前，仍需企业数据分类分级、敏感实体词典、外发审批和模型供应商合规评估。

## 当前边界
- 四类数据库连接器已具备配置自动化测试；目标企业内网的真实网络、TLS、Oracle service name/SID、SQL Server 实例及只读权限仍需联调。
- Agent 当前是只读辅助能力，未接入 LangGraph 多 Agent 编排、知识库检索或自动工作流。
- 当前不具备完整字段级 DLP、外发审批、企业级密钥托管和生产级高可用能力；部署前仍需完成安全评审和生产环境加固。

## MySQL 测试库（可选）

仓库提供一个隔离的 MySQL 8.0 测试库，包含虚构的 LED 封装制造场景数据结构：生产线、物料、设备、生产订单、质量检验、不良记录，以及一个视图。所有样例数据均为虚构，不包含企业真实数据。

### 启动

先复制并编辑环境变量文件，必须修改 PostgreSQL、MySQL root 和只读账号密码（不要使用示例值）：

```bash
cp .env.example .env
```

启动测试 MySQL：

```bash
docker compose --profile mysql-test up -d
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

后端启动时会自动、幂等地添加名为“ MySQL 测试数据库（mes_test）”的数据源，连接配置为 `mysql-test:3306`，密码环境变量名为 `MYSQL_TEST_READER_PASSWORD`。打开工作台“数据源管理”，找到该数据源，点击测试连接，再采集元数据；无需手工新增数据源。

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
