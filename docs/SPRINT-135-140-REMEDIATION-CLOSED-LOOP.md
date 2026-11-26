# Sprint 135–140：整改证据与闭环报表

## 本轮交付
- 任务证据记录 API：以现有 governance_records 存储，避免新增数据库表/迁移。
- 任务证据列表 API：按 task_id 返回证据元信息。
- 任务闭环运营报告：汇总任务状态、逾期、证据覆盖率，并按来源/部门拆分。
- 审计记录：证据创建行为写入 audit_logs。

## API
- GET/POST `/api/v1/governance/tasks/{task_id}/evidence`
- GET `/api/v1/governance/tasks-closed-loop-report`

Evidence payload fields: evidence_type, title, description, reference_url. No binary upload; references should be internal URLs or descriptive records. The report explicitly does not treat evidence as independent verification or automatic acceptance.

## Limitations / acceptance
- Storage uses existing Record table; task evidence JSON metadata is not a substitute for immutable file storage.
- Closed task evidence is read-only; evidence cannot be added after task closure.
- Current report aggregation loads task and evidence rows into application memory; consider SQL aggregation/indexing as scale grows.
- Test file added; test execution and CI status are not yet verified.
