# Sprint 153–158 — lifecycle timeline and acceptance metrics

## Delivered frontend enhancements
- Task-detail lifecycle timeline combines creation metadata, evidence records, review records and close metadata when available.
- Task acceptance report summary displayed in the detail view: total, reviewed, accepted, returned, unreviewed and acceptance rate.
- Evidence and review events are presented chronologically by record timestamps (the timeline sections are rendered in event group order; individual API records use backend descending order).

## Existing backend dependencies
- `GET /api/v1/governance/tasks/{task_id}/evidence`
- `GET /api/v1/governance/tasks/{task_id}/reviews`
- `GET /api/v1/governance/tasks-acceptance-report`

## Caveats / next refinement
- Timeline is an assembled view, not a unified immutable lifecycle event store. Task assignment and start events may not be independently timestamped in the task model.
- Current implementation groups task creation, evidence, reviews and closure rather than sorting every event by a normalized timestamp. A follow-up should normalize timestamps and sort.
- Report aggregation semantics follow the existing endpoint; metrics should not be interpreted as department performance ratings.
- Frontend build, API integration and browser smoke tests still need to be executed.
