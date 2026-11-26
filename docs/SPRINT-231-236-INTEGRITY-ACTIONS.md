# Sprint 231–236 · Review-integrity anomaly handling

## Delivered
- `GET /api/v1/governance/review-integrity-actions`: paginated action registry, governance:read.
- `POST /api/v1/governance/review-integrity-actions`: create/update action status and note, governance:write; unique logical identity is category + issue record ID (application-level deduplication).
- `GET /api/v1/governance/review-integrity-action-summary`: aggregate registered actions by status and category.
- Persisted via existing `Record` category `review_integrity_action`, with AuditLog records; no migration and no edits to review events or historical review records.

## Workflow
Statuses: 待处理 / 处理中 / 已解决 / 已确认非问题. Updates reuse the same action record for a category+ID pair. These are human disposition notes, not automatic integrity repairs or proof of remediation.

## Limitations
- Registry does not currently render a dedicated frontend page or bind directly to the expanded diagnostic issue list; UI integration remains next work.
- Deduplication is application-level and not transactionally unique; concurrent requests may create duplicates.
- No automatic repair, deletion, or mutation of historical review records.
- Automated test file added; execution, CI, frontend build and deployment are not confirmed.
