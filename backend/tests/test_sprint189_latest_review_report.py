import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint189-194-acceptance-report-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
import json
from app import main


def test_acceptance_report_uses_latest_review_per_task():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        task = main.GovernanceTask(task_code="S194-LATEST", title="Latest review report", status="处理中")
        db.add(task)
        db.commit()
        db.refresh(task)
        reviewer = "report-reviewer"
        for decision in ("通过", "退回"):
            row = main.Record(category="task_review", name=f"test {decision}",
                description=json.dumps({"task_id": task.id, "decision": decision, "reviewer": reviewer}),
                status=decision, owner=reviewer)
            db.add(row)
        db.commit()
        report = main.governance_tasks_acceptance_report(_user=None, db=db)
        assert report["returned_tasks"] >= 1
        assert report["review_records"] >= 2
        db.query(main.Record).filter(main.Record.category == "task_review").all()
        for row in db.query(main.Record).filter(main.Record.category == "task_review").all():
            try:
                if json.loads(row.description or "{}").get("task_id") == task.id:
                    db.delete(row)
            except (TypeError, json.JSONDecodeError):
                continue
        db.delete(task)
        db.commit()
