# Sprint 243–248 · Integrity anomaly detail and action history

## Delivered API changes
- `GET /api/v1/governance/review-event-integrity-detail?category=...&record_id=...`: read-only locator details for event-linked categories, including task and legacy review context when resolvable; legacy-review categories return a safely parsed payload.
- `GET /api/v1/governance/review-integrity-action-history?category=...&record_id=...`: returns up to 100 recorded status/note changes for a registered anomaly.
- Updates to the existing action API append a bounded (last 100) history item with status, note, actor, timestamp and prior status.

## Data boundaries
- All endpoints require governance:read; existing update endpoint still requires governance:write.
- No source audit/review record is repaired, rewritten, or deleted.
- History is stored within the existing governance Record JSON description; no schema migration.
- History is application-managed, not immutable cryptographic audit evidence; privileged DB edits can alter it.

## Remaining UI work
- Frontend should call detail endpoint when selecting an issue and render task/event/legacy payload with null-safe fields.
- Render action history chronologically and add controls for page-size / offset to diagnostics and action lists.
- Existing UI remains limited to its current first 200 rows; pagination UI not included in this sprint.
- Build, tests, CI, and deployment have not been verified in this session.
