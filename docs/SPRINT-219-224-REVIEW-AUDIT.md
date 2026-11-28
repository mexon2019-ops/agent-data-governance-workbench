# Sprint 219–224: Review history and integrity audit

Added read-only endpoints:
- `GET /api/v1/governance/tasks/{task_id}/review-history`: unified event/legacy review history with source labels and chronological ordering.
- `GET /api/v1/governance/review-event-integrity`: identifies event rows with missing task references, missing legacy links, or invalid decisions.

These endpoints are read-only and operate on the workbench database. They do not alter source systems or perform migration. CI is required before considering release.
