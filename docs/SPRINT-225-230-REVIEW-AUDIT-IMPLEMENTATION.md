# Sprint 225–230: Review audit reliability implementation

## Implemented in this change
- Added `GET /api/v1/governance/review-event-integrity-expanded`: read-only diagnostics with issue categories and bounded pagination (limit 1–200, offset >= 0). Categories include orphan task events, missing legacy references, invalid decisions, duplicate task events per task, unlinked legacy review records, and malformed legacy review records.
- Added `GET /api/v1/governance/tasks/{task_id}/review-history/export-v2`: CSV export with timestamp/scope metadata, CSV quoting via csv.writer, UTF-8 BOM, and a 2,000-row bounded export limit.
- Regression test coverage added to the Sprint 225 test file for diagnostics and export-v2.

## Limits and risks
- Diagnostic implementation currently reads all events, tasks and legacy review records to build a global issue list before pagination; large deployments may require SQL-based streaming/counting and pagination in future hardening.
- Export-v2 reads the full review history for a task and rejects above 2,000 items; use the paginated history endpoint for larger histories.
- No automatic data repair, deletion, or task status changes.
- Registered evidence and review events are workflow artifacts; they do not prove source-data remediation.
- CI and test execution have not been confirmed for this commit.

## API permissions
- Read-only diagnostics and export require `governance:read`.
- The new APIs do not modify audit history.
