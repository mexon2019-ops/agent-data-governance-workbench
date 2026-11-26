# Sprint 165–170 — Release verification hardening

## Sprint 165 — CI baseline
- Confirmed latest PR-head workflow success: backend pytest, Alembic upgrade, backend startup, frontend dev startup and browser smoke.
- Regression fix for nullable task priority is included in the verified head.

## Sprint 166 — Frontend production build
- Added `npm run build` to the GitHub Actions frontend install/build sequence.
- Build outcome is pending CI for the workflow-change commit.

## Sprint 167 — Schema compatibility
- CI applies Alembic migrations to a fresh SQLite database before startup.
- Existing database upgrade/rollback rehearsal remains a deployment task; CI fresh-database migration is not evidence of production migration safety.

## Sprint 168 — Security review scope
- Verify source credentials are stored as environment-key references, source database access remains read-only, audit records avoid raw source data and RBAC is enforced.
- These are review items, not claims of a completed security audit.

## Sprint 169 — Docker rehearsal
- Requires a test/internal host and synthetic metadata. No Docker deployment is asserted in this work.

## Sprint 170 — Release gate
- Require successful backend CI, frontend production build, migration rehearsal, RBAC/security review, operator walkthrough and deployment rollback plan.
- PR #44 remains draft and unmerged.


## Build defect found and corrected
- Workflow run 178 added production frontend build and failed at TypeScript parsing in `frontend/src/App.tsx` navigation array due literal escaped newline sequences.
- Corrected navigation block to use actual line breaks in commit `3b33226c28bb3aa9bf926178caf5eec443feeb4c`.
- Re-run CI on the repaired commit is pending; do not mark frontend build as passed until workflow confirms.
