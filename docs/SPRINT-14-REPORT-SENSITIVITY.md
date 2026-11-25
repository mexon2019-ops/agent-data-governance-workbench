# Sprint 14 — FineReport report sensitivity governance

## API
- `GET /api/v1/finereport/reports/{report_id}/sensitivity-assessment`: derive an advisory level from metadata-column classifications reachable only through human-approved report lineage. Includes classified and unclassified column summaries. Read-only.
- `POST /api/v1/finereport/reports/{report_id}/sensitivity-review`: human review and override, persists reviewer, timestamp, rationale and lineage table IDs.
- `GET /api/v1/finereport/sensitivity-reviews`: review ledger.

## Safety and limitations
- Requires governance read/write permissions.
- Preview-only lineage is not used. Only confirmed lineage records are considered.
- The recommendation is the maximum classified level among linked metadata columns. If there is no confirmed lineage, the recommendation remains `未分级`.
- Recommendations require human review; the submitted level can differ from the suggested level, with rationale captured.
- This is not a report output inspection and cannot guarantee that every rendered report field is covered. Report/dataset lineage coverage is a prerequisite for stronger conclusions.
- No SQL execution or external LLM calls.
