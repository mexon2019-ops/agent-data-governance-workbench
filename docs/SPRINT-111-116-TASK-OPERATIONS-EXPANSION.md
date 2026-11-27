# Sprint 111–116: Governance Task Operations Expansion

This backlog/specification is prepared against the current PR #44 branch and its existing task-generation/lifecycle APIs. It is intentionally a design and acceptance artifact; no runtime feature is claimed as implemented in this document.

## Sprint 111 — Generation rules
Use the existing Record table (category `task_generation_rule`) for an initial configuration prototype to avoid a new table/migration. Rule records should include source key in name, enabled/disabled status, and structured description/config JSON only after a schema validation layer is introduced. Rule CRUD must be governance:write; reads governance:read. Initially support checklist, mapping-review, and quality-run sources. Default behavior must be explicitly documented and backwards-compatible; disabled sources must not generate tasks. Validate rule keys and avoid arbitrary executable expressions.

Acceptance: rules list, create/update, enable/disable, audit logging, invalid rule rejection, and generation endpoint respects enabled flag. Do not treat description text as executable code.

## Sprint 112 — Manual priority overrides
Before persistence, add a priority field only through a reviewed schema migration. Values: high, medium, low. Preserve derived priority as a suggestion, not an authority. Record override actor, timestamp, and reason; audit every change. Avoid adding fields via unreviewed runtime ALTER operations.

Acceptance: override API, validation, reason required, audit trace, priority payload displays override and suggestion separately.

## Sprint 113 — Assignment rules
Use explicit mapping rules (source type, business domain/department, default owner) with deterministic precedence. Do not guess people from names or source SQL. If no mapping exists, leave unassigned and return a clear reason. Assignment must be previewable before bulk application.

Acceptance: preview endpoint, dry-run mode, apply mode with audit trail, and no assignment when ambiguous.

## Sprint 114 — Notification outbox
Implement an internal notification outbox rather than immediately sending email or external messages. Each notification should store recipient, channel, event, content template key, status, retry count, and timestamps. Avoid sensitive source record values in message bodies. Integrations remain optional and require explicit configuration.

Acceptance: outbox listing and status API, retry/backoff controls, recipient validation, no external send by default.

## Sprint 115 — Operations dashboard
Add a task operations dashboard showing volume by source/status/priority/department, overdue counts, aging buckets, assignment coverage, and closure rate. Aggregations must state their scope, include pagination or bounded queries where detail rows are used, and avoid presenting metrics as HR performance scores.

Acceptance: dashboard endpoint and UI, filters, loading/error/empty states, and export option.

## Sprint 116 — Closure verification
Introduce a distinct verification stage for tasks requiring evidence. Closing tasks should not automatically imply verified remediation. Provide verifier, verification result, note, and timestamp. Existing tasks remain compatible and should be handled by migration/backfill policy.

Acceptance: submit evidence/verification, reject self-verification when policy requires separation, audit trace, and report verified vs closed-but-unverified counts.

## Security and rollout notes
- All new endpoints remain behind existing RBAC permissions.
- No source business data writes; governance metadata only.
- Keep generation manual until rule configuration and deduplication constraints are validated.
- Existing application-level deduplication is vulnerable to concurrent duplicate creation; add a database uniqueness constraint or transactional strategy during a reviewed migration.
- Validate all database schema changes on SQLite and the supported production database before deployment.
- Run backend tests, frontend build, runtime smoke tests, and migration rehearsal before declaring readiness.
