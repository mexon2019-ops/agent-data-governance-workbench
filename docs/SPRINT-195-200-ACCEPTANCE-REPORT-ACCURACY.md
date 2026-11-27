# Sprint 195–200: Acceptance Report Accuracy

## Sprint 195 — Latest-review semantics
- Acceptance metrics must reflect the latest valid decision per task.
- Records are read in descending stable ID order.

## Sprint 196 — Invalid record tolerance
- Malformed JSON and unknown decisions are ignored.
- The first valid event per task is authoritative for this report.

## Sprint 197 — Regression test
- Add a regression test with multiple decisions for one task.
- Cleanup is scoped to the fixture task's records.

## Sprint 198 — Metrics interpretation
- Distinguish reviewed tasks from review-record count.
- Report remains an aggregate, not a substitute for a persisted task status.

## Sprint 199 — State persistence roadmap
- Evaluate a dedicated review-state field and event table in a future migration.
- Avoid retroactive status changes without migration design.

## Sprint 200 — Release validation
- Require CI plus staging operator review.
- Automated tests do not establish production readiness.

### Boundaries
- Workbench database only; source systems remain read-only.
- Review report is informational and must disclose its derivation.
