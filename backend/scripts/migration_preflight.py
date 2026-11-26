#!/usr/bin/env python3
"""Read-only migration preflight; does not upgrade or alter the database."""
import argparse
import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from alembic.runtime.migration import MigrationContext


def preflight(database_url: str, backup_file: str | None = None):
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected exactly one migration head; found: {heads}")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
            if current and not script.get_revision(current):
                raise RuntimeError(f"Database revision {current} is not present in this codebase")
            pending = list(script.iterate_revisions(heads[0], current)) if current else list(script.walk_revisions())
            dialect = conn.dialect.name
    finally:
        engine.dispose()
    if backup_file:
        backup = Path(backup_file)
        if not backup.is_file() or backup.stat().st_size <= 0:
            raise RuntimeError("Backup evidence file does not exist or is empty")
    return {"dialect": dialect, "current_revision": current or "unversioned",
            "target_revision": heads[0], "pending_revision_count": len(pending),
            "backup_evidence": backup_file or "not supplied (preflight does not enforce backup)"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--backup-file", help="Optional path to a non-empty backup/evidence file")\n    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL is required")
    try:
        result = preflight(args.database_url, args.backup_file)
    except Exception as exc:
        print(f"PRE-FLIGHT FAILED: {exc}", file=sys.stderr)
        return 1
    print("PRE-FLIGHT OK")
    for key, value in result.items():
        print(f"{key}: {value}")
    print("No migrations were applied. Take and verify a database backup before upgrade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
