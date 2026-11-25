# Sprint 12 — Confirm and persist report lineage

This sprint adds a governed approval endpoint to store a report/dataset mapping to catalog table IDs as an approval record. Retrieval is read-only and permission-gated.

- GET `/api/v1/finereport/reports/{report_id}/lineage-approved` requires governance:read
- POST `/api/v1/finereport/lineage/approve` requires governance:write
- Body: report_id, dataset, table_ids, optional notes
- Validates report inventory and every metadata table ID.
- Stores approval record using existing governance record storage; preserves approval timestamp and username.
- Does not execute SQL or promote preview automatically; approver explicitly submits chosen table IDs.

Frontend approval UX, revoke/edit workflow, and versioning are future work.
