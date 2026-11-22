# Agent 数据治理工作台

V0.2 MVP：八个工作台模块、FastAPI + PostgreSQL、数据源配置和数据库连通性测试框架。

## 页面
1. 治理总览
2. 数据源管理
3. 数据资产
4. 元数据目录
5. 数据标准
6. 数据质量
7. 治理任务
8. Agent 助手

## 技术栈
- 前端：React + TypeScript + Vite
- 后端：FastAPI + SQLAlchemy 2
- 元数据库：PostgreSQL
- 数据源适配器：SQL Server（pymssql）、Oracle（python-oracledb Thin mode）、MySQL（PyMySQL）、PostgreSQL（psycopg）
- 部署：Docker Compose + Nginx

## 启动
复制 `.env.example` 为 `.env`，设置 `POSTGRES_PASSWORD`，再执行：

```bash
docker compose up -d --build
```

访问 http://localhost:8080；API 文档 http://localhost:8000/docs。

## 数据源凭据管理
数据源表只保存密码环境变量名（例如 `MES_DB_PASSWORD`），不保存明文密码。请在后端容器的受控环境中注入对应变量。不要把真实密码提交到 Git。当前 Compose 示例尚未为业务数据库配置密码变量，需按实际环境通过 Docker secrets 或受控部署变量注入。

连接测试会执行只读的 `SELECT 1`。建议为源数据库创建最小权限只读账号，并通过网络策略限制访问。

## 当前实现边界
- 数据源配置、编辑、删除及连通性测试 API 已实现。
- 数据资产、元数据目录、数据标准、质量、任务共用治理记录 CRUD API。
- Agent 页面是交互骨架，尚未接入 LangGraph 或外部模型；不会把用户输入发送到第三方。
- 当前没有完整登录、RBAC、审批、审计、字段级脱敏和生产级密钥管理，不可直接暴露公网或作为生产系统使用。
- 数据源驱动在容器环境中的编译/系统依赖与目标数据库版本仍需部署验证。
