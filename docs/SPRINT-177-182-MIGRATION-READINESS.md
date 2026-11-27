# Sprint 177–182 — Migration readiness & release safety

## Scope
- 177: Repair preflight CLI syntax and JSON mode; make machine-readable output stable.
- 178: Expand preflight tests for CLI JSON success/error paths and backup evidence.
- 179: Add migration readiness report guidance: target environment, DB dialect, current/target revision, pending count.
- 180: Define operator checklist for backup/restore verification (manual evidence; no destructive automation).
- 181: Establish compatibility matrix test plan for SQLite CI and SQL Server/Oracle/MySQL/PostgreSQL deployment checks.
- 182: Release gate checklist for migration readiness and governance-workbench pilot deployment.

## Safety boundaries
- Preflight remains read-only and never applies migrations.
- Backup evidence checks only file presence/non-empty content; they do not verify restoreability.
- Production upgrade/restore steps remain operator-controlled, with verified backups and approval.
- Source-system database access remains read-only.

## CI follow-up
The preflight CLI test exposed a literal escaped newline in the script and missing JSON-mode output implementation. Fix commits were submitted; verify the newest Actions run against the latest PR head before considering the work validated.
