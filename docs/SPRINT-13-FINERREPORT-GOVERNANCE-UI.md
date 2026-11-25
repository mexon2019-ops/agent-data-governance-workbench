# Sprint 13 — FineReport Governance UI

## Scope
- Add a FineReport governance entry to the frontend navigation.
- List imported FineReport report inventory from the report inventory API.
- Trigger read-only lineage preview for a report.
- Display preview JSON with an explicit manual-review banner.
- No SQL execution, no automated approval, and no external LLM calls.

## API expectations
- GET /api/v1/finereport/reports
- GET /api/v1/finereport/reports/{report_id}/lineage-preview

The UI treats imported inventory as untrusted and only displays preview responses. Confirmed lineage remains a separate explicit approval workflow.

## Validation
Frontend CI/build validation required. API response shape and report identifiers should be verified against the deployment.
