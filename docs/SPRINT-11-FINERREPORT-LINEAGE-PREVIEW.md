# Sprint 11 — FineReport report lineage preview

## Scope
Build a safe, read-only preview that connects imported FineReport report inventory with the existing metadata catalog. SQL is never executed.

## API contract
- `GET /api/v1/finereport/reports/{report_id}/lineage-preview`
- Read report inventory records in category `finereport_report`.
- Extract SQL only from allowlisted inventory fields (`dataset_sql` and dataset objects containing `sql`).
- Use the conservative extractor in `finereport_service.py`.
- Match extracted table names against catalog table names and schema names case-insensitively; do not guess across ambiguous matches.
- Return per-dataset extracted references, catalog matches, unresolved references, and manual-review flag.

## Safety and quality
- No SQL execution, database probing, or outbound LLM call.
- SQL is treated as untrusted text and parsed only.
- CTEs, unresolved identifiers, and ambiguous catalog matches are marked for manual review.
- Report-level results should not be persisted as confirmed lineage until a human approves them.
- API should be read-only and require authenticated access consistent with existing report inventory endpoints.

## Acceptance criteria
1. Unknown report ID returns 404.
2. Reports with dataset SQL yield a preview; reports without SQL yield an empty/manual-review result.
3. Simple FROM/JOIN references are matched against metadata catalog.
4. Ambiguous and unmatched tables are clearly separated.
5. SQL is not executed or sent to external services.
6. Unit tests cover simple references, CTE/manual review, ambiguous matches, and missing report.
