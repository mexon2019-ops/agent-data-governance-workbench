import os,uuid,json
os.environ.setdefault("DATABASE_URL",f"sqlite:////tmp/sprint219-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET","test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_review_history_and_integrity_payload():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        task=main.GovernanceTask(task_code="S219-HISTORY",title="History fixture")
        db.add(task);db.commit();db.refresh(task)
        row=main.Record(category="task_review",name="legacy history",description=json.dumps({"task_id":task.id,"decision":"退回","reviewer":"fixture","comment":"legacy"}))
        db.add(row);db.commit();db.refresh(row)
        event=main.GovernanceReviewEvent(task_id=task.id,decision="通过",reviewer="reviewer",comment="event",legacy_record_id=row.id)
        db.add(event);db.commit()
        history=main.governance_task_review_history(task.id,_user=None,db=db)
        assert history["count"]==1 and history["history"][0]["source"]=="event"
        integrity=main.governance_review_event_integrity(_user=None,db=db)
        assert integrity["integrity_ok"]
        db.delete(event);db.delete(row);db.delete(task);db.commit()
