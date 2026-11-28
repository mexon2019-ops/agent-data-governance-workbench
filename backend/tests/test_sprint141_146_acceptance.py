import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint141-146-review-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_independent_review_requires_evidence_and_reviewer_not_owner():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        db.query(main.Record).filter(main.Record.category.in_(["task_evidence","task_review"])).delete(synchronize_session=False)
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code=="S141-REVIEW").delete(synchronize_session=False)
        task=main.GovernanceTask(task_code="S141-REVIEW",title="验收流程测试",status="处理中",owner="owner-user")
        db.add(task);db.commit();db.refresh(task)
        reviewer=type("UserFixture",(),{"username":"reviewer-user"})()
        owner=type("UserFixture",(),{"username":"owner-user"})()
        try:
            main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="通过"),reviewer,db)
            assert False,"should require evidence"
        except main.HTTPException as e: assert e.status_code==409
        try:
            main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="通过"),owner,db)
            assert False,"owner should not self-review"
        except main.HTTPException as e: assert e.status_code==403
        evidence_user=type("UserFixture",(),{"username":"owner-user"})()
        main.add_governance_task_evidence(task.id,main.GovernanceTaskEvidenceIn(title="证据材料",description="整改结果"),evidence_user,db)
        review=main.review_governance_task(task.id,main.GovernanceTaskReviewIn(decision="通过",comment="验收通过"),reviewer,db)
        assert review["decision"]=="通过"
        report=main.governance_tasks_acceptance_report(_user=reviewer,db=db)
        assert report["accepted_tasks"]>=1
        db.query(main.Record).filter(main.Record.category.in_(["task_evidence","task_review"])).delete(synchronize_session=False)
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code=="S141-REVIEW").delete(synchronize_session=False)
        db.commit()
