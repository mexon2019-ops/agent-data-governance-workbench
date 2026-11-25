# Sprint 15–17 Integration & Validation

## Current dependency / PR state
- Sprint 13 UI: PR #27, base `main`, pending merge and CI.
- Sprint 14 sensitivity backend: PR #29, base Sprint 13 branch, pending merge and validation.
- Sprint 15 field-to-standard APIs currently reside on the Sprint 14 branch. Keep them gated by approved lineage and published standard versions. Before merge, split or explicitly re-scope the PR so reviewers can see the complete stacked dependency.

## Sprint 15 field standard governance
APIs:
- `GET /api/v1/finereport/reports/{report_id}/standard-candidates`
- `POST /api/v1/finereport/reports/{report_id}/standard-review`
- `GET /api/v1/finereport/standard-coverage`

### Safety / behavior acceptance
1. Candidate and review endpoints require governance permissions.
2. Candidate generation is scoped to latest approved lineage only; missing lineage returns 409.
3. Candidate matching is deterministic and heuristic. Score is ranking only, not accuracy or confidence.
4. Review accepts only published standards and versions; reviewed column must be within approved lineage.
5. Positive review writes a mapping; negative review is recorded in a review ledger and must not be interpreted as a positive mapping.
6. Coverage is review-ledger based; latest review decision per report/column wins.
7. No source SQL execution, business-row retrieval, or external LLM call in this workflow.

### Known hardening items before release
- Confirm coverage's report display-name field is sourced from imported inventory JSON, not the record description field (which may be serialized inventory).
- Ensure latest negative decision cannot leave a stale active mapping visible as current; expose effective review decision distinctly from stored mapping.
- Validate duplicate mapping upsert behavior and transaction rollback on ledger failure.
- Reject malformed lineage ledger entries and non-integer table IDs; preserve clear 409/404 behavior.
- Add API tests for permission denial, absent approved lineage, column outside lineage, unpublished version, positive/negative decision, and latest-review coverage calculation.

## Sprint 16 governance overview
Proposed read-only endpoint: `GET /api/v1/governance/overview` (governance:read).
Dashboard metrics: active issues, closed issues, overdue issues, closure rate, severity distribution, status distribution, department distribution, quality-run success/failure summary, and latest issues.
Rules: overdue means due_date before current date and status not closed; closure-rate denominator should be clearly defined and exclude draft/non-actionable states if those exist. All counts should be calculated from governance records, never source business rows.

## Sprint 17 standards-driven rule candidates
Preview: `GET /api/v1/quality/rules/standard-preview`
Create: `POST /api/v1/quality/rules/from-standard-mappings`
- Only confirmed standard mappings are eligible.
- Required standards propose completeness rules; explicit parseable numeric limits propose range rules.
- No inferred enum or format rules.
- Preview must be read-only; created rules disabled by default and idempotent by rule code.
- Selected codes must be validated against preview results; use governance:write.
- No external LLM or source business data access.

## Release / regression checklist
- [ ] CI checks green for each stacked PR.
- [ ] Run backend test suite and frontend build.
- [ ] Exercise APIs with authorized and unauthorized users.
- [ ] Test with no lineage, approved lineage, stale/rejected review, published/unpublished standards.
- [ ] Confirm source database remains read-only and no report SQL executes during preview.
- [ ] Verify no secrets in browser storage, logs, commits, or API payloads.
- [ ] Validate Docker Compose clean startup and Alembic migration.
- [ ] Smoke test UI: login, report inventory, lineage preview, standard candidate review, coverage.
- [ ] Recheck PR base/head ordering; merge Sprint 13 before Sprint 14/15 dependency.
