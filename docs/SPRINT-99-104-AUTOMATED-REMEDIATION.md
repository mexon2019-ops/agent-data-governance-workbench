# Sprint 99–104: Automated governance remediation

## Implemented
- Sprint 99: POST /api/v1/governance/tasks/generate-from-checklist creates task per failed asset checklist item. Existing source key (asset ID + check key) is deduplicated; source type asset_checklist.
- Sprint 100: POST /api/v1/governance/tasks/generate-from-mappings generates tasks for mappings in 待核验 / 不符合. Mapping ID is the source key; repeated runs skip existing tasks.
- Sprint 101: POST /api/v1/governance/tasks/generate-from-quality-runs generates tasks from recorded QualityRun entries with failed_count > 0, without rescanning source data. Quality run ID is the dedup key.
- Sprint 102: automatic generation endpoints expose created and skipped-existing counts, task source metadata, and audit events; no duplicate source tasks are created on repeat runs.
- Sprint 103: task list API supports owner filter; frontend has owner filter.
- Sprint 104: generation feedback and existing task-summary dashboard support basic operational tracking (pending, in-progress, overdue, closure rate).

## Security and boundaries
- Each generator requires governance:write.
- Data sources are not queried by these generators; they use stored governance metadata, mappings, and recorded quality run results.
- All generated tasks are auditable.
- This is a manual trigger, not a scheduler; no notification or auto-assignment is implemented.

## Validation limitations
- Backend test execution, frontend build, and browser tests have not been verified in this session.
- Review database schema initialization/migration behavior and race-condition-safe deduplication before deployment; source-key dedup currently uses application-level lookup, not a unique constraint.
- Generated task volume can grow: mapping and quality-run generators currently cap source selection to 500 rows per call for quality runs; mapping generator may process all pending/noncompliant mappings.
