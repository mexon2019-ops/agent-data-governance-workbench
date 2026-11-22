# Sprint 0：登录认证与 RBAC 基础

## 本次交付

- 用户、角色、权限及多对多关联表。
- PBKDF2-HMAC-SHA256 密码哈希（每个用户独立随机盐）。
- HMAC-SHA256 签名的短期 Bearer Token，默认有效期 8 小时。
- 登录、当前用户、管理员用户列表、创建用户、角色列表 API。
- 四个内置角色：`admin`、`data_steward`、`auditor`、`viewer`。
- 受权限保护的用户/角色管理接口。
- 审计中间件从服务端验证过的 Bearer Token 解析真实用户名，不接受客户端自报身份。
- Alembic revision `0003_auth_rbac` 创建认证和授权表。

## 首次启动配置

复制 `.env.example` 为本地 `.env`，使用独立随机值替换：

```bash
openssl rand -hex 32
```

将生成值设置为 `AUTH_SECRET`。另外设置至少 16 位的 `BOOTSTRAP_ADMIN_PASSWORD`。不要将真实 `.env` 提交到 Git。

启动：

```bash
docker compose up -d --build
```

系统首次启动时创建默认角色与权限；若 admin 用户不存在，则用 `BOOTSTRAP_ADMIN_PASSWORD` 创建初始 `admin`。后续重启不会覆盖已有管理员密码。请在首次登录后按企业账号规范管理凭据。

## API

- `POST /api/v1/auth/login`：用户名密码登录，返回 Bearer Token。
- `GET /api/v1/auth/me`：获取当前用户、角色和权限。
- `GET /api/v1/admin/users`：需要 `user:manage`。
- `POST /api/v1/admin/users`：需要 `user:manage`，密码至少 12 位。
- `GET /api/v1/admin/roles`：需要 `user:manage`。

## 角色初始权限

| 角色 | 权限 |
|---|---|
| admin | 用户管理、治理读写、数据源管理、审计查看 |
| data_steward | 治理读写、数据源管理 |
| auditor | 治理只读、审计查看 |
| viewer | 治理只读 |

## 安全边界与下一步

当前迭代为认证、角色和授权提供基础能力；本 PR 仅对用户/角色管理 API 实施 RBAC，尚未将全部历史数据源、元数据、治理写接口统一加上认证依赖，也尚未完成前端登录页、Token 生命周期/主动吊销、登录失败限流、密码重置和细粒度资源级权限。因此，在这些工作完成前，不应把当前版本视为已完成生产级访问控制。

后续 Sprint 应：
1. 前端登录、Token 安全存储、退出登录和 401 跳转。
2. 将治理读取/写入、数据源管理和审计查看权限逐个绑定到 API。
3. 增加登录失败限流、账户停用、密码重置与 Token 吊销策略。
4. 为审计查询增加管理员专用 API 和分页筛选。
