# Sprint 33–36 Governance hardening

## Sprint 33 — Batch metadata classification suggestions
- Read-only endpoint: GET /api/v1/governance/classification-suggestions?limit=500
- Uses field names and types only, bounded limit; returns advisory suggestions.
- No business data rows, no automatic classification changes.

## Sprint 34 — Standards review baseline
- Existing standards versioning and mapping-review flow retained.
- Candidate rule endpoint is scoped to published standards and confirmed mappings.
- Mapping review/coverage must remain human-approved; no lineage bypass.

## Sprint 35 — Standard-driven quality rule preview
- GET /api/v1/governance/standard-rule-preview
- Proposes completeness for required fields and numeric range only for simple parseable range notation.
- Candidates disabled and not persisted; arbitrary expressions are rejected by design.
- Review and manual rule creation/enablement remains separate.

## Sprint 36 — Integration / safety
- No migration or source-data writes.
- API bounded results, read-only metadata context.
- CI and Docker validation are release gates; this PR is not considered deployable until those checks pass.
