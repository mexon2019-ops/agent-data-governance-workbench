# Sprint 0：用户认证与 RBAC 基础

## 本次交付

- 用户、角色、权限、角色权限关联四张表。
- Alembic revision `0003_iam`，兼容新库基线已创建表和旧库从 `0002` 升级两种路径。
- 使用 Argon2 对密码进行哈希；数据库不保存明文密码。
- 使用 HS256 JWT bearer token，默认有效期 60 分钟，可通过 `JWT_EXPIRE_MINUTES` 调整。
- `POST /api/v1/auth/token` 登录。
- `GET /api/v1/auth/me` 获取当前用户、角色和权限。
- `GET /api/v1/admin/users` 和 `GET /api/v1/admin/roles` 使用 RBAC 权限依赖保护。
- 一次性管理员引导脚本：`backend/scripts/bootstrap_admin.py`。
- 写操作审计从经过签名校验的 JWT 读取用户 ID；未认证请求仍记录为 anonymous，不信任身份请求头。

## 首次部署步骤

1. 备份工作台数据库。
2. 设置强随机 `JWT_SECRET_KEY`（至少 32 个字符，建议使用密码管理器生成 48 字节以上随机值）。
3. 先执行数据库迁移：`alembic upgrade head`。
4. 在 backend 容器/虚拟环境设置 `BOOTSTRAP_ADMIN_USERNAME` 和 `BOOTSTRAP_ADMIN_PASSWORD`（至少 14 位）。
5. 执行一次：`PYTHONPATH=. python scripts/bootstrap_admin.py`。
6. 立即清除引导环境变量，不要把管理员密码写入镜像、Compose 文件、Git 或日志。
7. 使用 OAuth2 password form 登录，获取 bearer token。

示例：

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=YOUR_ADMIN' \
  --data-urlencode 'password=YOUR_PASSWORD'
```

## 权限模型与当前边界

- 权限码采用 `资源:对象:动作` 风格，例如 `iam:user:read`、`iam:role:read`。
- 管理员引导仅授予用户读取和角色读取权限；未来增加管理操作时必须显式授予对应权限。
- 本 PR 只对 IAM 管理查询接口启用 RBAC；现有治理 API 尚未全部加上认证依赖，不能据此宣称全系统已经强制登录。下一迭代需逐路由接入权限，并同步更新前端登录态。
- JWT 密钥缺失或弱于 32 字符时，登录/身份校验返回服务配置错误，不提供硬编码默认密钥。
- 生产部署还应启用 HTTPS、限制登录尝试频率、制定密码重置与账号停用流程，并将密钥放入内网 Secret 管理设施。

## 自动化验证

CI 增加：
- 密码哈希/验证测试。
- 未登录访问 `/auth/me` 返回 401。
- 正确密码登录后可用 JWT 获取当前用户信息。
- 完整 Alembic 迁移和既有元数据采集测试。
