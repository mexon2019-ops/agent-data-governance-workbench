# Sprint 19 — Governance trends API

- Add GET /api/v1/governance/trends with governance:read authorization.
- Return a rolling 12-month series of issue-created and issue-closed counts.
- Aggregate only governance issue lifecycle timestamps; do not read source database rows.
- No migrations or external model calls.

## Metric definitions
- created: issue created_at within calendar month.
- closed: issue closed_at within calendar month.
- Historical overdue status is intentionally not reconstructed because state-change history is not currently available.
