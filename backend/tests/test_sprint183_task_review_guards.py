import os
import uuid
os.environ.setdefault("DATABASE_URL", f"sqlite:////tmp/sprint183-188-review-test-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main
import pytest
import json


def cleanup(db, task):
    rows=db.query(main.Record).filter(main.Record.category.in_(["task_evidence","task_review"])).all()
    linked_ids=[]
    for row in rows:
        try:
            if json.loads(row.description or "{}").get("task_id")==task.id: linked_ids.append(row.id)
        except (TypeError,json.JSONDecodeError): pass
    events=db.query(main.GovernanceReviewEvent).filter(main.GovernanceReviewEvent.legacy_record_id.in_(linked_ids)).all() if linked_ids else []
    for event in events: db.delete(event)
    rows=db.query(main.Record).filter(main.Record.category.in_(["task_evidence","task_review"])).all()
    for row in rows:
        try:
            if json.loads(row.description or "{}").get("task_id")==task.id: db.delete(row)
        except (TypeError,json.JSONDecodeError): pass
    db.delete(task);db.commit()


def test_task_review_requires_evidence_and_independent_reviewer():
    main.Base.metadata.create_all(main.engine)
    # Prevent SQLite primary-key reuse from colliding with historical event links.
    with main.SessionLocal() as db:
        db.execute(main.delete(main.GovernanceReviewEvent).where(main.GovernanceReviewEvent.legacy_record_id.is_not(None)))
        db.commit()
    with main.SessionLocal() as db:
        task=main.GovernanceTask(task_code="S183-REVIEW-"+uuid.uuid4().hex[:8],title="Review flow",status="处理中",owner="worker")
        db.add(task);db.commit();db.refresh(task)
        worker=type("UserFixture",(),{"username":"worker"})()
        reviewer=type("UserFixture",(),{"username":"reviewer"})()
        with pytest.raises(main.HTTPException) as no_evidence:
            main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="通过"),reviewer,db)
        assert no_evidence.value.status_code==409
        with pytest.raises(main.HTTPException) as self_review:
            main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="退回"),worker,db)
        assert self_review.value.status_code==403
        main.add_governance_task_evidence(task.id,main.GovernanceTaskEvidenceIn(title="整改证明"),worker,db)
        accepted=main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="通过",comment="核验"),reviewer,db)
        assert accepted["decision"]=="通过"
        cleanup(db,task)


def test_review_decision_validation_and_return_path():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        task=main.GovernanceTask(task_code="S183-RETURN-"+uuid.uuid4().hex[:8],title="Return flow",status="处理中",owner="owner")
        db.add(task);db.commit();db.refresh(task)
        owner=type("UserFixture",(),{"username":"owner"})()
        reviewer=type("UserFixture",(),{"username":"reviewer"})()
        main.add_governance_task_evidence(task.id,main.GovernanceTaskEvidenceIn(title="Evidence"),owner,db)
        with pytest.raises(main.HTTPException) as invalid:
            main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="invalid"),reviewer,db)
        assert invalid.value.status_code==422
        returned=main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="退回",comment="补充材料"),reviewer,db)
        assert returned["decision"]=="退回"
        cleanup(db,task)
