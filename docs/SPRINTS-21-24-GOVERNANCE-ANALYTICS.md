# Sprints 21–24 — Governance analytics and triage

## Sprint 21 — Standard coverage
- Read-only `GET /api/v1/governance/standard-coverage`
- Counts published versions, confirmed mappings, pending/rejected reviews, business-domain rollup and unmapped-column inventory (capped at 500 rows).
- Scope explicitly limited to collected metadata and published standard versions.

## Sprint 22 — Quality analytics
- Read-only `GET /api/v1/governance/quality-analytics`
- Aggregates stored quality runs, pass rate, and per-rule latest results.
- Does not execute quality queries or access source data.

## Sprint 23 — Classification analytics
- Read-only `GET /api/v1/governance/classification-analytics`
- Distribution by classification level, field coverage, table rollups and unmapped inventory (capped at 500 rows).
- Classification remains human-confirmed.

## Sprint 24 — Governance priority queue
- Read-only `GET /api/v1/governance/priorities`
- Advisory scoring for open governance issues and latest failed enabled-rule results.
- Includes rationale; does not automatically assign owners or trigger remediation.

All endpoints require `governance:read`. No schema migrations, source business-row access, write SQL, external LLM calls or automatic remediation.
