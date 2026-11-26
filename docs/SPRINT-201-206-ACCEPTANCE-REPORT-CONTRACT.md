# Sprint 201–206: Acceptance reporting regression and review-state roadmap

## Objectives
- Strengthen the acceptance-report regression contract around latest valid decisions.
- Verify malformed/unknown decision events do not override valid decisions.
- Verify counts are task-level, not event-level.
- Keep test data isolated and cleanup scoped to fixture-owned records.
- Document a safe path from metadata-backed review records to a formal event/state model.

## Regression assertions
- The newest valid decision per task is the effective decision.
- Invalid JSON and unsupported decision values are ignored.
- Older valid events do not override newer valid events.
- Totals are task counts; multiple events for one task count once.
- Test cleanup must not delete records belonging to other fixtures or users.

## Review-state model proposal (future migration, not implemented here)
- Introduce a dedicated immutable review event table, keyed to task ID, actor, decision, comment, event timestamp, and request correlation ID.
- Keep task operational status distinct from acceptance decision.
- Acceptance report reads the event table and applies a documented ordering tie-breaker (timestamp plus event ID).
- Backfill existing Record metadata conservatively; malformed payloads remain quarantined and are not auto-converted.
- Migration must be reversible and preflighted; no migration is run in this sprint.

## Scope and safeguards
- Workbench database only. Source databases remain read-only.
- No external LLM invocation.
- This sprint adds regression coverage and design documentation only; no production state migration.
