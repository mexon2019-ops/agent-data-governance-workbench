# Sprint 147–152 — Task evidence and independent acceptance UI

## Scope
This sprint package is intended to expose the already implemented backend evidence and independent-review endpoints from the Governance Task Center.

## Backend endpoints (existing)
- GET/POST `/api/v1/governance/tasks/{task_id}/evidence`
- GET/POST `/api/v1/governance/tasks/{task_id}/reviews`
- GET `/api/v1/governance/tasks-acceptance-report`

## UI implementation checklist
- [ ] Open a task detail view showing task fields, ownership, due date and action plan.
- [ ] Show task evidence history and allow evidence metadata submission (title, description, reference URL).
- [ ] Show independent-review history and allow `通过` / `退回` decisions.
- [ ] Show returned tasks and allow further evidence submission/resubmission.
- [ ] Display lifecycle timeline combining task status, evidence, and review records.
- [ ] Add acceptance-report summary metrics and export.

## Constraints
- The API enforces evidence-required approval and owner self-review prohibition; UI checks are supplementary.
- Evidence records are metadata only; no binary upload/storage is provided in this sprint.
- Review approval is separate from task closure.
- No automatic verification or assignment is implied.

## Validation required before release
- Frontend typecheck/build and tests.
- API tests against supported database setup.
- Browser smoke test with non-owner reviewer, owner self-review rejection, no-evidence rejection, returned task and subsequent evidence, and task closure distinct from approval.
