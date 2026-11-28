import os
import uuid
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/sprint207-review-events-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_review_event_table_and_dual_write_are_linked():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        baseline=main.governance_tasks_acceptance_report(_user=None,db=db)
        task=main.GovernanceTask(task_code="S207-EVENT-"+uuid.uuid4().hex[:8],title="Event table",status="处理中",owner="worker")
        db.add(task);db.commit();db.refresh(task)
        worker=type("UserFixture",(),{"username":"worker"})()
        reviewer=type("UserFixture",(),{"username":"reviewer"})()
        main.add_governance_task_evidence(task.id,main.GovernanceTaskEvidenceIn(title="Evidence"),worker,db)
        result=main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="通过"),reviewer,db)
        event=db.query(main.GovernanceReviewEvent).filter_by(task_id=task.id).one()
        assert event.decision=="通过"
        assert event.reviewer=="reviewer"
        assert event.legacy_record_id==result["id"]
        report=main.governance_tasks_acceptance_report(_user=None,db=db)
        assert report["accepted_tasks"]==baseline["accepted_tasks"]+1
        event_id=event.id
        record_id=result["id"]
        evidence_rows=db.query(main.Record).filter(main.Record.category=="task_evidence").all()
        for row in evidence_rows:
            import json
            if json.loads(row.description or "{}").get("task_id")==task.id:
                db.delete(row)
        db.query(main.Record).filter(main.Record.id==record_id).delete()
        db.query(main.GovernanceReviewEvent).filter(main.GovernanceReviewEvent.id==event_id).delete()
        db.delete(task);db.commit()
