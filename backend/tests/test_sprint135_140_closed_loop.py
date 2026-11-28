import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint135-140-evidence-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_task_evidence_and_closed_loop_report():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        db.query(main.Record).filter(main.Record.category=="task_evidence").delete(synchronize_session=False)
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code.like("S135-%")).delete(synchronize_session=False)
        task=main.GovernanceTask(task_code="S135-EVIDENCE",title="证据记录测试",status="处理中")
        db.add(task);db.commit();db.refresh(task)
        user=type("UserFixture",(),{"username":"test-user"})()
        evidence=main.add_governance_task_evidence(task.id,main.GovernanceTaskEvidenceIn(title="整改截图说明",description="完成整改并附验证截图"),user,db)
        assert evidence["task_id"]==task.id
        listed=main.list_governance_task_evidence(task.id,_user=user,db=db)
        assert listed["total"]==1
        report=main.governance_tasks_closed_loop_report(_user=user,db=db)
        assert report["summary"]["with_evidence"]>=1
        db.query(main.Record).filter(main.Record.category=="task_evidence").delete(synchronize_session=False)
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code=="S135-EVIDENCE").delete(synchronize_session=False)
        db.commit()
