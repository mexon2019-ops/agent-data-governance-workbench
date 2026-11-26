import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from migration_preflight import preflight


def test_preflight_reports_head_and_pending_for_unversioned_database(tmp_path):
    db = tmp_path / "preflight.db"
    result = preflight(f"sqlite:///{db}")
    assert result["dialect"] == "sqlite"
    assert result["current_revision"] == "unversioned"
    assert result["pending_revision_count"] > 0


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
