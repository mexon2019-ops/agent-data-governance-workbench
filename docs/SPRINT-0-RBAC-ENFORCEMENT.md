# Sprint 0：治理 API 权限收口

## 已实施的路由权限

| API 范围 | 所需权限 |
|---|---|
| `GET /api/v1/dashboard` | `governance:read` |
| `GET /api/v1/records` | `governance:read` |
| 记录新增、修改、删除 | `governance:write` |
| 数据源查询、创建、修改、删除、连接测试 | `datasource:manage` |
| 元数据目录查询、字段详情 | `governance:read` |
| 元数据采集及采集历史 | `datasource:manage` |
| Agent 治理建议入口 | `governance:write` |
| `GET /api/v1/admin/audit-logs` | `audit:read` |
| 用户/角色管理 | `user:manage` |

`/health` 和登录接口保持公开。未携带 Token 返回 401；已登录但缺少权限返回 403。

## 前端

- 增加登录页面，调用 `POST /api/v1/auth/login`。
- Token 仅保存在当前浏览器标签页的 sessionStorage；退出登录会清除。
- 刷新页面时通过 `GET /api/v1/auth/me` 校验 Token。
- 所有 API 请求自动附加 Bearer Token。
- 按当前用户权限隐藏无权访问的导航和写操作入口；后端权限校验仍是最终安全边界。

## 审计日志

管理员可以通过 `GET /api/v1/admin/audit-logs?offset=0&limit=50` 分页读取审计日志。最大单页 200 条。日志不包含请求体和凭据。

## 验收

CI 包含：
- 无 Token 访问 dashboard 返回 401。
- admin 登录后 dashboard、数据源和审计接口可用。
- viewer 可读取治理概览，但无法读取数据源配置或写入治理记录（403）。
- 浏览器自动化先登录，再逐页截图和执行业务 smoke test。

## 注意事项

当前 Token 为服务端 HMAC 签名的短期 Bearer Token，默认 8 小时。当前没有 refresh token、服务端主动吊销、登录失败限流或密码重置流程。生产部署应通过 HTTPS 访问，并保护 AUTH_SECRET。前端使用 sessionStorage 限制持久时间，但仍需防范 XSS。
