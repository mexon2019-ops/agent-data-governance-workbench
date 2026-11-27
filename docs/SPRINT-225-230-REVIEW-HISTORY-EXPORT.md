# Sprint 225–230 — Review history pagination and export

- Sprint 225–226: Review-history API supports bounded pagination (limit 1–200, offset >= 0), returning total count and has_more.
- Sprint 227–228: CSV export endpoint for task review history, bounded to 200 records per export, UTF-8 BOM for spreadsheet compatibility.
- Sprint 229: regression tests for pagination and export payload.
- Sprint 230: API contract documentation.

## Endpoints
- GET /api/v1/governance/tasks/{task_id}/review-history?limit=100&offset=0
- GET /api/v1/governance/tasks/{task_id}/review-history/export

Both endpoints require governance:read. Export is bounded and intentionally rejects tasks with more than 200 history entries; use pagination for larger histories. Data is sourced from review-event rows and unlinked legacy records for the requested task only.
