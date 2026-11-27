# Sprint 57 — Mapping review action and audit

- `PATCH /api/v1/standards/mappings/{mapping_id}/review` updates a single mapping status and note.
- Valid statuses: 待核验, 已落标, 不符合; note max 2000 characters.
- Requires `governance:write`; missing mappings return 404 and invalid status returns 422.
- Writes a row to the existing `audit_logs` table recording actor, action, resource, request ID, method, path and status code.
- Audit record excludes secrets and source business rows.
- The action only updates governance metadata; it does not modify source databases.
- CI and integration testing remain required before considering this complete.
