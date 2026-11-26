# Sprint 189–194: Governance Review Reliability

## Sprint 189 — Fixture isolation
- Scope cleanup of review/evidence records to the fixture task ID.
- Avoid broad deletion of shared test database records.

## Sprint 190 — Review decision consistency
- Verify review decisions are persisted as audit records and remain queryable.
- Confirm evidence linkage is explicit and task-scoped.

## Sprint 191 — Return-to-remediation path
- Ensure returned tasks can accept new evidence and be resubmitted.
- Retain prior review decisions; do not overwrite review history.

## Sprint 192 — API contract
- Verify conflict responses for missing evidence and forbidden self-review.
- Keep validation failures distinct from permission failures.

## Sprint 193 — Regression gate
- Run backend suite, migration checks, frontend build, and browser smoke tests.
- Treat failures as blockers; no bypassing gates.

## Sprint 194 — Acceptance
- Review evidence and history manually in staging.
- Record operator acceptance separately from automated test results.

### Safety boundaries
- Test cleanup must be scoped to fixture task IDs only.
- No source database writes; governance workbench database only.
- CI validation does not substitute for staging acceptance.
