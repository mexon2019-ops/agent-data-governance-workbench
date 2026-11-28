# Sprint 53–56: governance review and auditability

## Goals
Move the asset/standard mapping experience toward review-ready operation without touching source data.

### Sprint 53 — Mapping review queue
- Queue by status (待核验/已落标/不符合), standard, business domain and owner.
- Reviewer action requires governance:write; read views require governance:read.
- Keep mapping notes and timestamps visible.

### Sprint 54 — Governance action audit
- Record governance mutations with actor, object, action, timestamp and outcome.
- Avoid logging secrets, connection strings, raw business rows or full external prompts.
- Audit logs are append-only from the UI; no destructive edit controls.

### Sprint 55 — Asset review checklist
- Checklist fields: business definition, owner, department, domain, classification, standard mapping, quality coverage and review date.
- Completion is an evidence-based status, not an automatic compliance claim.

### Sprint 56 — Review/report export
- Generate a governance review summary from stored metadata and workflow records only.
- Clearly label incomplete evidence and non-verified claims.
- No source-database write actions.

## Acceptance and safeguards
- Permission checks enforced on backend endpoints.
- Validate inputs, paginate large queues, and test both positive and negative paths.
- LLM remains optional and opt-in; send only redacted summary data.
- Manual review is required for publication, classification and closure.


## Sprint 53 UI increment (committed)
- Added a dedicated `标准映射审核` navigation page.
- Displays standard/version, source/table, field/type, mapping status, notes and timestamp.
- Filters by mapping status and paginates in 100-row increments using the review-queue API.
- Read-only view: no approval mutation is exposed yet; status changes remain outside this page until the audit-backed review action is implemented.
