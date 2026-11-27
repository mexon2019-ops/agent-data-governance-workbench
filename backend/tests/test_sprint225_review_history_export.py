import os, uuid, json
os.environ.setdefault("DATABASE_URL",f"sqlite:////tmp/sprint225-history-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET","test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_review_history_pagination_and_csv_export():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        task=main.GovernanceTask(task_code="S225-"+uuid.uuid4().hex[:8],title="Paginated history")
        db.add(task);db.commit();db.refresh(task)
        rows=[]
        for decision in ("通过","退回","通过"):
            row=main.Record(category="task_review",name="fixture",description=json.dumps({"task_id":task.id,"decision":decision,"reviewer":"reviewer","comment":"fixture"}))
            db.add(row);db.flush()
            event=main.GovernanceReviewEvent(task_id=task.id,decision=decision,reviewer="reviewer",comment="fixture",legacy_record_id=row.id)
            db.add(event);rows.append((row,event))
        db.commit()
        page=main.governance_task_review_history(task.id,limit=2,offset=0,_user=None,db=db)
        assert page["count"]==3 and len(page["history"])==2 and page["has_more"]
        second=main.governance_task_review_history(task.id,limit=2,offset=2,_user=None,db=db)
        assert len(second["history"])==1 and not second["has_more"]
        export=main.export_governance_task_review_history(task.id,_user=None,db=db)
        assert export.media_type.startswith("text/csv")
        assert "decision" in export.body.decode("utf-8-sig")
        for row,event in rows: db.delete(event);db.delete(row)
        db.delete(task);db.commit()


def test_expanded_integrity_report_and_export_v2():
    with main.SessionLocal() as db:
        task=main.GovernanceTask(task_code="S225X-"+uuid.uuid4().hex[:8],title="Expanded diagnostics")
        db.add(task);db.commit();db.refresh(task)
        legacy=main.Record(category="task_review",name="fixture",description=json.dumps({"task_id":task.id,"decision":"通过","reviewer":"reviewer","comment":"comma, quote \\\""}))
        db.add(legacy);db.flush()
        event=main.GovernanceReviewEvent(task_id=task.id,decision="通过",reviewer="reviewer",comment="comma, quote \\"",legacy_record_id=legacy.id)
        db.add(event);db.commit()
        report=main.governance_review_event_integrity_expanded(limit=10,offset=0,_user=None,db=db)
        assert report["event_count"]>=1 and report["issues"] is not None
        export=main.export_governance_task_review_history_v2(task.id,_user=None,db=db)
        decoded=export.body.decode("utf-8-sig")
        assert "export_generated_at" in decoded and "decision" in decoded and "comma, quote" in decoded
        db.delete(event);db.delete(legacy);db.delete(task);db.commit()
