# Sprint 0：工程基础建设

## 本次变更

### 1. 数据库迁移纳入 Alembic
- 新增 `backend/alembic.ini`、迁移环境和基线版本 `0001_baseline`。
- 容器启动时先执行 `alembic upgrade head`，成功后才启动 FastAPI。
- FastAPI lifespan 不再调用 `Base.metadata.create_all`，避免应用启动时隐式改动业务表结构。
- CI 在 API smoke test 前显式执行迁移。
- 基线迁移用于接管当前 SQLAlchemy 模型结构；后续结构变更必须新增迁移版本，不得修改已在共享环境执行的基线文件。

### 2. CORS 收敛
- 删除允许任意来源的 `*` 配置。
- 使用 `CORS_ALLOWED_ORIGINS` 逗号分隔配置。
- 默认允许本地 Nginx/开发地址：`http://localhost:8080`、`http://127.0.0.1:8080`、`http://localhost:5173`。
- 内网部署时应将其改成实际前端域名/协议。

## 部署与运维

Docker Compose 构建后，backend 容器会自动迁移数据库：

```bash
docker compose up -d --build
docker compose logs -f backend
```

查看当前迁移版本：

```bash
docker compose exec backend alembic current
docker compose exec backend alembic history
```

手动执行升级：

```bash
docker compose exec backend alembic upgrade head
```

## 重要注意事项

- 首次基线迁移适用于当前项目已有的空白/新建工作台数据库。
- 如果已有旧版工作台数据库，其中已经存在业务表但没有 `alembic_version`，不要直接运行自动升级。应先备份数据库，再按迁移接管流程确认现有结构与基线一致，并通过受控的 stamp/校验步骤接管。
- 生产环境升级前必须备份 PostgreSQL，并在测试环境演练恢复。
- Alembic 解决结构版本管理，不等于已经完成认证、RBAC、审计或生产安全加固。

## 本次验收

CI 应完成：
1. 安装 Alembic。
2. 在独立 SQLite 测试库执行 `alembic upgrade head`。
3. 启动 FastAPI 并通过 health check。
4. 执行现有元数据采集单元测试和浏览器 smoke test。
