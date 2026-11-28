# Sprint 171–176 — Migration Safety & Release Upgrade Controls

## Objectives
Create a safer, repeatable database upgrade process before expanding governance features. Database upgrades are operator-controlled; the workbench does not automatically modify business-source databases.

## Sprint 171 — Version inventory
- Use Alembic revision identifiers as the authoritative schema version.
- Record application release and schema revision separately.
- Avoid treating SQLAlchemy create_all as a production upgrade mechanism.

## Sprint 172 — Upgrade preflight
- Require database connectivity and a readable Alembic version table.
- Report current revision and target head; flag multiple heads.
- Require operator review of upgrade SQL (alembic upgrade head --sql where supported) and migration notes.
- Abort when the preflight cannot establish a safe state.

## Sprint 173 — Backup and protection
- Before upgrading, operators must create and verify a database backup/snapshot.
- Record backup location, timestamp, and restore verification in release evidence.
- Do not automate destructive backup or restore operations in the application.

## Sprint 174 — Failure and rollback
- Migrations must be transactional where supported; explicitly document dialect limitations.
- Downgrade is not assumed to be safe. Prefer restore-from-verified-backup for production recovery.
- Capture migration logs and retain the pre-upgrade revision.

## Sprint 175 — Compatibility test matrix
- CI must validate fresh database migration to head.
- Upgrade-path testing must start from a representative prior schema snapshot, not merely empty DB.
- Include SQLite smoke tests but acknowledge they do not substitute for production DB dialect rehearsals.

## Sprint 176 — Release gate
- Release checklist: backup verified, migration review, revision recorded, upgrade rehearsal, health check, application smoke tests, recovery plan.
- Keep PR draft and do not merge without explicit approval.
- No production deployment or rollback rehearsal is claimed by this document.

## Current evidence
CI Run 182 passed backend unit tests, migrations and health startup but failed TypeScript production build due to an implicit-any callback in task-operations CSV export. Fixed with explicit callback annotations in App.tsx commit 95bf1eb. Await a fresh CI result.
