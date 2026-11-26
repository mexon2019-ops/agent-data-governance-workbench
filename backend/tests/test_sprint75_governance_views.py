import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint75-governance-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")

from app import main


def test_asset_checklist_handles_nullable_fields_and_reports_counts():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        source_name = "s75-checklist-fixture"
        source = db.query(main.DataSource).filter_by(name=source_name).first()
        if source:
            db.delete(source)
            db.commit()
        source = main.DataSource(name=source_name, db_type="mysql", host="localhost",
            port=3306, database="fixture", username="readonly", password_env_key="FIXTURE_PASSWORD")
        db.add(source); db.commit(); db.refresh(source)
        table = main.MetadataTable(source_id=source.id, schema_name="fixture", table_name="s75_table")
        db.add(table); db.commit(); db.refresh(table)
        asset = main.DataAsset(asset_code="S75_NULL_FIXTURE", name="空字段兼容测试资产",
            metadata_table_id=table.id, description=None, owner=None, owner_department=None,
            business_domain=None, sensitivity_level=None)
        db.add(asset); db.commit(); db.refresh(asset)
        checklist = main.asset_review_checklist(_user=object(), db=db)
        row = next(x for x in checklist["items"] if x["asset_code"] == "S75_NULL_FIXTURE")
        assert row["completed"] == 0
        assert row["total_checks"] == 7
        report = main.governance_review_report(_user=object(), db=db)
        assert report["asset_count"] >= 1
        assert any(x["asset_code"] == "S75_NULL_FIXTURE" for x in report["incomplete_assets"])
        db.delete(asset); db.delete(table); db.delete(source); db.commit()


def test_audit_query_filters_and_pagination():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        log = main.AuditLog(request_id="s75-test-request", actor="s75-test-actor",
            action="PATCH", resource="mapping:s75", http_method="PATCH",
            path="/api/v1/test", status_code=200)
        db.add(log); db.commit()
        result = main.governance_audit(actor="s75-test-actor", resource="mapping:s75",
            limit=10, offset=0, _user=object(), db=db)
        assert result["total"] >= 1
        assert any(x["request_id"] == "s75-test-request" for x in result["items"])
        db.delete(log); db.commit()
