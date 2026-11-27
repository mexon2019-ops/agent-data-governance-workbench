# Sprint 87–92 — Governance task center

## Scope
This increment establishes a metadata-only task lifecycle API. It does not modify source database records.

## Lifecycle
`待处理 -> 处理中 -> 已关闭`. Closing requires a result/review note. Closed tasks cannot be edited.

## APIs
- POST `/api/v1/governance/tasks`: create (governance:write)
- GET `/api/v1/governance/tasks`: list/filter/paginate (governance:read)
- GET `/api/v1/governance/tasks/{task_id}`: details (governance:read)
- PATCH `/api/v1/governance/tasks/{task_id}`: update basic fields (governance:write)
- POST `/api/v1/governance/tasks/{task_id}/start`: start (governance:write)
- POST `/api/v1/governance/tasks/{task_id}/close`: close with note (governance:write)
- GET `/api/v1/governance/tasks-summary`: task metrics (governance:read)

## Task fields
Code, title, type, source type/id, description, action plan, owner, department, creator, status, due date, close note and timestamps.

## Sprint grouping
- 87: task model and API create/list/detail
- 88: edit, assignment fields, filters and pagination
- 89: lifecycle transition validation
- 90: audit trail and summary metrics
- 91: lifecycle automated test module committed; execution not confirmed
- 92: implementation notes and acceptance outline

## Known limitations / next acceptance
- No task-center frontend UI yet; APIs are the foundation and UI remains the next implementation slice.
- Source-driven task creation (asset checklist, classification/quality exceptions) is not automated yet.
- Tests are committed but not yet confirmed executed.
- Task assignment currently records owner and department fields; no notification or escalation service.
- No migration or live deployment has been confirmed in this increment; confirm schema migration strategy before deploying to an existing database.
