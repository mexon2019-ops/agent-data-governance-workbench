# Sprint 207–212: Governance review event engine

## Implemented in this increment
- Dedicated ORM event model `GovernanceReviewEvent`.
- Migration `0010_governance_review_events`, chained from revision 0009.
- Review writes create a dedicated event and retain the legacy Record entry for compatibility.
- Acceptance report prefers dedicated events and falls back to legacy records only for tasks without dedicated events.
- Regression test exercises event linkage and report aggregation.

## Event schema
- task_id: associated governance task
- reviewer: reviewer username
- decision: accepted values currently enforced by the review endpoint (通过/退回)
- comment: review comment
- legacy_record_id: optional unique bridge to the retained Record row
- created_at: event timestamp

## Migration and operational safety
- This sprint does not automatically backfill historical events.
- Existing historical records remain in the legacy Record store and are read as fallback.
- Migration is reversible and adds only a dedicated event table and indexes.
- Migration must be run only after backup and migration preflight; no production database is touched here.
- Source business databases remain read-only.

## Follow-on
- Carefully designed, bounded historical backfill with idempotency and audit.
- Add request correlation / ordering semantics and task-state reconciliation.
- API list endpoint can expose event history with legacy bridge behavior.
