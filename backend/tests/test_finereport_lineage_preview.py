import json
from sqlalchemy import select
from app import main


def test_finereport_lineage_preview_matches_catalog_and_flags_unknown():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        report_id = "SPRINT11_LINEAGE_FIXTURE"
        old = db.scalar(select(main.Record).where(main.Record.category == "finereport_report", main.Record.name == report_id))
        if old:
            db.delete(old)
            db.commit()
        source_name = "sprint11-lineage-source"
        source = db.scalar(select(main.DataSource).where(main.DataSource.name == source_name))
        if not source:
            source = main.DataSource(name=source_name, db_type="mysql", host="localhost", port=3306,
                database="fixture", username="readonly", password_env_key="FIXTURE_PASSWORD")
            db.add(source)
            db.commit()
            db.refresh(source)
        table = db.scalar(select(main.MetadataTable).where(main.MetadataTable.source_id == source.id,
            main.MetadataTable.schema_name == "sales", main.MetadataTable.table_name == "orders"))
        if not table:
            table = main.MetadataTable(source_id=source.id, schema_name="sales", table_name="orders",
                table_type="TABLE", column_count=2)
            db.add(table)
            db.commit()
            db.refresh(table)
        db.add(main.Record(category="finereport_report", name=report_id, status="已导入",
            description=json.dumps({"name":"订单分析报表","datasets":[{"name":"订单数据","sql":"SELECT * FROM sales.orders JOIN missing_table m ON 1=1"}]})))
        db.commit()
        result = main.finereport_lineage_preview(report_id, db)
        assert result["preview_only"] is True
        assert result["sql_executed"] is False
        assert result["review_required"] is True
        dataset = result["datasets"][0]
        assert dataset["matched"][0]["table_name"] == "orders"
        assert dataset["unresolved"] == ["missing_table"]
        db.delete(db.scalar(select(main.Record).where(main.Record.category == "finereport_report", main.Record.name == report_id)))
        db.commit()


def test_finereport_lineage_preview_unknown_report_404():
    from fastapi import HTTPException
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        try:
            main.finereport_lineage_preview("NO_SUCH_SPRINT11_REPORT", db)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError("expected report not found")
