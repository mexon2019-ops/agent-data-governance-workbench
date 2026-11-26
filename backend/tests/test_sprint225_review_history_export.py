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
