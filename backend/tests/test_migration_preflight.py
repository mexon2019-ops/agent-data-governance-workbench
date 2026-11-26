import sys
from pathlib import Path

from alembic.config import Config
from alembic.command import upgrade

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from migration_preflight import preflight


def alembic_config(database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_preflight_reports_head_and_pending_for_unversioned_database(tmp_path):
    db = tmp_path / "preflight.db"
    result = preflight(f"sqlite:///{db}")
    assert result["dialect"] == "sqlite"
    assert result["current_revision"] == "unversioned"
    assert result["pending_revision_count"] > 0


def test_preflight_reports_zero_pending_after_upgrade(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = tmp_path / "upgraded.db"
    url = f"sqlite:///{db}"
    upgrade(alembic_config(url), "head")
    result = preflight(url)
    assert result["current_revision"] == result["target_revision"]
    assert result["pending_revision_count"] == 0


def test_preflight_backup_evidence_must_be_nonempty(tmp_path):
    db = tmp_path / "preflight.db"
    evidence = tmp_path / "backup.txt"
    evidence.write_text("verified backup", encoding="utf-8")
    result = preflight(f"sqlite:///{db}", str(evidence))
    assert result["backup_evidence"] == str(evidence)


def test_preflight_rejects_empty_backup_evidence(tmp_path):
    db = tmp_path / "preflight.db"
    evidence = tmp_path / "empty.txt"
    evidence.write_text("", encoding="utf-8")
    try:
        preflight(f"sqlite:///{db}", str(evidence))
    except RuntimeError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("empty backup evidence must be rejected")


def test_cli_json_output_is_machine_readable(tmp_path, monkeypatch, capsys):
    import json
    import migration_preflight

    db = tmp_path / "cli.db"
    monkeypatch.setattr("sys.argv", ["migration_preflight", "--database-url", f"sqlite:///{db}", "--json"])
    assert migration_preflight.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"
    assert output["migration_applied"] is False
    assert "pending_revision_count" in output


def test_cli_json_error_is_machine_readable(tmp_path, monkeypatch, capsys):
    import json
    import migration_preflight

    db = tmp_path / "error.db"
    missing = tmp_path / "missing-backup.txt"
    monkeypatch.setattr("sys.argv", ["migration_preflight", "--database-url", f"sqlite:///{db}", "--backup-file", str(missing), "--json"])
    assert migration_preflight.main() == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "error"
    assert output["migration_applied"] is False
    assert "backup evidence" in output["error"].lower()
