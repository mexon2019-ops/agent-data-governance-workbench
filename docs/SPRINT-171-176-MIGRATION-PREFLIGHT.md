# Sprint 171–176: migration preflight utility

Added a read-only preflight utility at `backend/scripts/migration_preflight.py`.

## Usage
From the backend directory:
```bash
DATABASE_URL='sqlite:///./dev.db' python scripts/migration_preflight.py
python scripts/migration_preflight.py --database-url 'sqlite:///./dev.db' --backup-file ./backup-verification.txt
```

The utility verifies connectivity, a single Alembic head, whether the current revision is recognized, and counts pending revisions. An optional backup-evidence file must exist and be non-empty. The utility does not create backups, upgrade schemas, or validate backup contents/restorability. Its output is a preflight aid, not authorization to deploy.

## Release checklist
- Freeze application writes or arrange a maintenance window where required.
- Take a database-specific backup and verify restore in a rehearsal.
- Run preflight against the target environment.
- Review migration operations and dialect compatibility.
- Apply migration in staging; validate application and business workflows.
- Plan rollback/forward-fix; restore only with a reviewed procedure.
- Preserve logs and sign-off.
