# Sprint 105–110: Task Governance Operations

## Delivered code in this iteration
- **Priority derivation (Sprint 106):** public task payload includes a derived priority (high/medium/low) without adding a DB column or requiring migration. Keyword-based high priority is conservative but should be reviewed by governance operators.
- **Department metrics (Sprints 109–110):** new read-only endpoint `GET /api/v1/governance/tasks-department-summary` summarizes task totals, pending/in-progress/closed, overdue, high priority, and closure rate by department. Missing department is grouped as `未分配部门`.
- **Compatibility:** task schema remains unchanged; source database remains read-only; APIs remain permission-gated.

## Design backlog / limitations
- Sprint 105 generation rule administration is not persisted or wired into generation yet; generation endpoints remain manually triggered and fixed-rule.
- Sprint 107 assignment is not automated; generated tasks may remain unassigned.
- Sprint 108 notification delivery is not implemented. This iteration avoids storing outbound notification data or calling external services.
- Priority is heuristic and derived from title/description/task_type/source_type. It is not an authoritative severity classification.
- The department summary endpoint is an aggregate snapshot, not a performance ranking; it should not be used for disciplinary decisions without data quality review.

## Acceptance / validation
- Code changes committed to PR #44 branch.
- Automated tests and frontend build have not been run in this connector session. GitHub Actions status must be checked after commit.
