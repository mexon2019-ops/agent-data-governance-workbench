# Sprint 255–260 — Integrity diagnostics category filtering

## Delivered
- The expanded review-event integrity diagnostics endpoint accepts a validated `category` query value (or `全部`) and returns filtered issue count, `total`, offset, limit and has_more.
- The frontend audit anomaly page exposes a category selector and requests the filtered diagnostic dataset when it changes.
- Diagnostic logic remains read-only; category filtering does not mutate event or legacy records.

## API
`GET /api/v1/governance/review-event-integrity-expanded?limit=100&offset=0&category=duplicate_task_event`

Supported values: `全部`, `orphan_task_event`, `missing_legacy_link`, `invalid_event_decision`, `duplicate_task_event`, `unlinked_legacy_review`, `malformed_legacy_record`.

## Limitations / follow-up
- Backend still builds the diagnostic issue set in memory before applying offset/limit. This is API pagination, not database-level pagination.
- Frontend requests up to 200 filtered issues at offset zero and paginates that fetched page locally. Full server-driven paging and audit-log correlation remain follow-up work.
- Runtime tests, frontend build, and deployment were not run as part of this commit.
