# Sprint 20 — Governance maturity indicators

## Scope
- Read-only API: GET /api/v1/governance/maturity (governance:read).
- Dashboard displays six transparent ratio metrics and a simple equal-weight reference score.
- Indicators: asset registration, metadata table count as collected-scope indicator, published/confirmed standard mapping, field classification, enabled quality-rule coverage, issue closure.
- No source business-row access, SQL mutation, external model calls, or schema migration.

## Interpretation and limitations
- Metadata collection metric reflects tables already collected in the workbench; it is not a denominator for the full enterprise estate.
- Asset and quality-rule coverage are measured against the collected metadata scope.
- Standard mapping only counts mappings to published versions with confirmed-like mapping status.
- Score is a reference indicator, not audit certification or a formal maturity assessment. Validate scope and definitions with governance owners before using in management reporting.
