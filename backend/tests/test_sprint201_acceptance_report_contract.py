import os
import json
import uuid

os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/sprint201-206-report-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_acceptance_report_latest_valid_decision_and_scope():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        task = main.GovernanceTask(task_code="S206-REPORT", title="Report regression", status="处理中")
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id
        rows = [
            main.Record(category="task_review", name="older accepted", description=json.dumps({"task_id": task_id, "decision": "通过"})),
            main.Record(category="task_review", name="newer returned", description=json.dumps({"task_id": task_id, "decision": "退回"})),
            main.Record(category="task_review", name="malformed", description="{not-json"),
            main.Record(category="task_review", name="unknown", description=json.dumps({"task_id": task_id, "decision": "未知"})),
        ]
        db.add_all(rows)
        db.commit()
        report = main.governance_tasks_acceptance_report(_user=None, db=db)
        assert report["returned_tasks"] == 1
        assert report["accepted_tasks"] == 0
        assert report["reviewed_tasks"] == 1
        assert report["unreviewed_tasks"] == max(0, report["total_tasks"] - 1)
        assert report["review_records"] >= 4
        # Clean only rows and task created by this fixture.
        for row in db.query(main.Record).filter(main.Record.category == "task_review").all():
            try:
                if json.loads(row.description or "{}").get("task_id") == task_id or row.name in ("malformed", "unknown"):
                    db.delete(row)
            except (TypeError, json.JSONDecodeError):
                if row.name == "malformed":
                    db.delete(row)
        db.delete(task)
        db.commit()
