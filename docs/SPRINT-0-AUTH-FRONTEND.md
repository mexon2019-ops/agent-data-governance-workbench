# Sprint 0：前端登录与 API 权限控制

## 登录流程

- `POST /api/v1/auth/login` 使用 JSON 用户名/密码登录。
- 前端将短期 Bearer Token 保存在 sessionStorage，页面刷新后调用 `GET /api/v1/auth/me` 校验。
- 所有工作台 API 请求附加 Authorization Bearer Token。
- Token 失效时清除会话并返回登录界面。
- 退出登录清除当前标签页 Token。

## API 访问策略

除健康检查和登录接口外，所有 `/api/v1/*` API 均要求有效 Token。

- 治理数据读取：`governance:read`
- 治理记录写入、Agent 执行：`governance:write`
- 数据源配置、连接测试、元数据同步：`datasource:manage`
- 用户/角色管理：`user:manage`
- 审计查询：`audit:read`

数据源列表同样需要 `datasource:manage`，避免只读用户看到内网主机、数据库名和连接账号等基础设施信息。

## CI 配置

当前 GitHub Actions 使用固定的**仅限 CI 的测试口令**初始化 admin。仓库管理员需要在 Settings → Secrets and variables → Actions → Variables 新建：

- Name：`CI_ADMIN_PASSWORD`
- Value：与 CI workflow 中 `BOOTSTRAP_ADMIN_PASSWORD` 完全一致的 CI 专用测试口令。

不得使用企业真实管理员口令。变量缺失时，浏览器 smoke test 的登录步骤会失败；后端单元测试和 Alembic 迁移仍可能通过。

## 生产安全边界

- 必须通过 HTTPS 暴露工作台。
- `AUTH_SECRET` 使用独立高熵随机值，禁止提交到 Git。
- sessionStorage 仍受 XSS 风险影响；正式生产建议升级到 HttpOnly + Secure + SameSite Cookie 或企业 OIDC/SSO。
- 当前尚未实现 Refresh Token、主动吊销、登录失败限流、密码重置和细粒度行级权限。
