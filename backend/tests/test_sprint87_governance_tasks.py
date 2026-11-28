import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint87-governance-task-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_task_lifecycle_create_start_close_and_summary():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code.like("GT-UT-%")).delete(synchronize_session=False)
        db.commit()
        user=type("UserFixture",(),{"username":"sprint87-test"})()
        payload=main.GovernanceTaskCreate(title="测试治理闭环",description="synthetic test",owner="fixture",owner_department="测试")
        created=main.create_governance_task(payload,user=user,db=db)
        task_id=created["id"]
        assert created["status"]=="待处理"
        started=main.start_governance_task(task_id,main.GovernanceTaskAction(note="开始"),user=user,db=db)
        assert started["status"]=="处理中"
        closed=main.close_governance_task(task_id,main.GovernanceTaskAction(note="已完成测试整改"),user=user,db=db)
        assert closed["status"]=="已关闭"
        assert closed["close_note"]=="已完成测试整改"
        summary=main.governance_tasks_summary(_user=user,db=db)
        assert summary["closed"]>=1
        db.delete(db.get(main.GovernanceTask,task_id));db.commit()


def test_task_close_requires_note_and_valid_state():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        user=type("UserFixture",(),{"username":"fixture"})()
        task=main.GovernanceTask(task_code="GT-UT-STATE",title="状态验证测试")
        db.add(task);db.commit();db.refresh(task)
        import pytest
        with pytest.raises(main.HTTPException):
            main.close_governance_task(task.id,main.GovernanceTaskAction(note=""),user=user,db=db)
        db.delete(task);db.commit()
