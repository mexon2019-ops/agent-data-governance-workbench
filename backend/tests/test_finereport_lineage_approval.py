import json
from sqlalchemy import select
from app import main


def test_lineage_approval_persists_and_retrieves():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        rid = "SPRINT12_APPROVAL_FIXTURE"
        report = db.scalar(select(main.Record).where(main.Record.category=="finereport_report",main.Record.name==rid))
        if not report:
            db.add(main.Record(category="finereport_report",name=rid,status="已导入",description=json.dumps({"name":"test"})))
            db.commit()
        source = db.scalar(select(main.DataSource).where(main.DataSource.name=="sprint12-approval-fixture"))
        if not source:
            source=main.DataSource(name="sprint12-approval-fixture",db_type="mysql",host="localhost",port=3306,database="fixture",username="ro",password_env_key="FIXTURE_PASSWORD")
            db.add(source); db.commit(); db.refresh(source)
        table= db.scalar(select(main.MetadataTable).where(main.MetadataTable.source_id==source.id,main.MetadataTable.table_name=="approval_table"))
        if not table:
            table=main.MetadataTable(source_id=source.id,schema_name="test",table_name="approval_table",table_type="TABLE",column_count=1)
            db.add(table);db.commit();db.refresh(table)
        payload=main.LineageApprovalIn(report_id=rid,dataset="fixture",table_ids=[table.id],notes="verified")
        result=main.approve_report_lineage(payload,_user=type("UserFixture",(),{"username":"fixture"})(),db=db)
        assert result["status"]=="已确认"
        listed=main.get_approved_report_lineage(rid,_user=object(),db=db)
        assert any(x["dataset"]=="fixture" and table.id in x["table_ids"] for x in listed)
        db.delete(db.scalar(select(main.Record).where(main.Record.id==result["id"])))
        db.commit()
