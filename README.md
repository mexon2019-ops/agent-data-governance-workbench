# Agent 数据治理工作台

内网部署的 Agent 数据治理工作台 MVP。第一阶段聚焦元数据、数据资产、数据标准、数据质量和治理任务；后续扩展 LangGraph Agent、数据脱敏网关及 FineReport 集成。

## 技术栈
- 前端：React + TypeScript + Vite
- 后端：FastAPI + SQLAlchemy
- 业务库：PostgreSQL
- 部署：Docker Compose

## 本地 Docker 启动
1. 复制 `.env.example` 为 `.env` 并设置强密码。
2. 执行 `docker compose up -d --build`。
3. 前端访问 http://localhost:8080；API 文档 http://localhost:8000/docs。

## 当前范围
本版本为开发骨架：基础治理实体 CRUD API 和演示前端。数据源连接器、真实元数据采集、Agent 模型调用、RBAC、审批及脱敏策略尚需后续开发和安全验证。

## 安全要求
- 不提交真实密码、Token、模型密钥或生产数据。
- 数据源凭据只保存密钥引用，不在业务表存明文密码。
- 连接生产源时使用只读账号并限制网络访问。
- 外部模型调用前必须经过脱敏和授权校验。
- 当前版本没有完整认证授权，不可直接暴露到公网或生产环境。
