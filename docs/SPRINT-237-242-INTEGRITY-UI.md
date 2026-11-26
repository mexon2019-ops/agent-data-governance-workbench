# Sprint 237–242 · Review integrity anomaly UI

## UI
Added an `integrity` page in the operations navigation. It loads:
- read-only expanded integrity diagnostics (up to 200 entries),
- action registry page (up to 200 entries),
- action status/category summary.

Rows expose issue category and record ID, current registration status and note, a JSON diagnostic detail panel, and a status/note prompt for users with governance:write. Read users can inspect the registry and diagnostics.

## API integration
Uses `GET /governance/review-event-integrity-expanded`, `GET /governance/review-integrity-actions`, `GET /governance/review-integrity-action-summary`, and `POST /governance/review-integrity-actions`.

## Boundaries / known gaps
- Diagnostics are bounded to the first 200 entries in this UI; paging controls are not yet implemented.
- Detail panel currently displays the diagnostic object only, not a fully resolved task/event/legacy record payload.
- Status updates use prompts, not a dedicated form.
- Existing application-level deduplication caveat remains.
- Frontend build, automated tests, CI and deployment were not verified in this work session.
- No source data or historical audit record repair/mutation.
