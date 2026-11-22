# Sprint 0：前端登录与 API 访问控制

## 前端登录

- 系统入口显示登录页。
- 登录通过 `POST /api/v1/auth/login` 获取 Bearer Token。
- Token 当前保存在浏览器 `sessionStorage`，关闭浏览器会话后清除。
- 页面初始化时调用 `/api/v1/auth/me` 校验会话。
- API 返回 401 时清除本地会话并回到登录页。
- 顶栏展示当前用户并提供退出登录。

## API 访问控制

- 除登录接口外，`/api/v1/*` 均要求有效 Bearer Token。
- 健康检查和 CORS OPTIONS 预检请求保持公开。
- 数据治理读取需要 `governance:read`。
- 治理记录写入需要 `governance:write`。
- 数据源新增、修改、删除、测试和元数据同步需要 `datasource:manage`。
- 用户和角色管理由接口级 `user:manage` 校验保护。
- 审计操作者从服务端验证后的 Token 解析，不信任客户端自报身份。

## 当前安全限制

这是第一阶段的基础访问控制，不等于完整生产身份平台。当前 Token 存在 sessionStorage，仍可被同源 XSS 读取；后续建议采用 HttpOnly、Secure、SameSite Cookie 或企业 SSO/OIDC。还需补充登录失败限流、Token 主动吊销/刷新、密码重置、账号锁定和资源级授权。

## CI 登录验证

浏览器冒烟测试使用仓库 Actions Secret `CI_ADMIN_PASSWORD` 作为 CI 管理员口令，并且该值必须与后端启动时的 `BOOTSTRAP_ADMIN_PASSWORD` 一致。不要将生产密码写入工作流、源码或公开仓库。若未配置该 Secret，当前浏览器冒烟步骤只能验证登录页渲染，不执行登录后的导航与 API 冒烟。
