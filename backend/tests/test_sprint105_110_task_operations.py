import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint105-task-ops-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_priority_heuristic():
    high=main.GovernanceTask(task_code="H",title="安全整改",task_type="整改")
    medium=main.GovernanceTask(task_code="M",title="质量异常整改",source_type="quality_run")
    low=main.GovernanceTask(task_code="L",title="完善说明",source_type="manual")
    assert main._task_priority(high)=="高"
    assert main._task_priority(medium)=="中"
    assert main._task_priority(low)=="低"
    legacy=main.GovernanceTask(task_code="LEGACY",title=None,description=None,task_type=None)
    assert main._task_priority(legacy)=="低"


def test_department_summary_aggregation():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code.like("S105-%")).delete(synchronize_session=False)
        db.add_all([
            main.GovernanceTask(task_code="S105-A",title="安全整改",owner_department="测试部门",status="待处理"),
            main.GovernanceTask(task_code="S105-B",title="普通任务",owner_department="测试部门",status="已关闭"),
        ])
        db.commit()
        user=type("UserFixture",(),{"username":"fixture"})()
        result=main.governance_tasks_department_summary(_user=user,db=db)
        dept=next(x for x in result["departments"] if x["department"]=="测试部门")
        assert dept["total"]==2 and dept["pending"]==1 and dept["closed"]==1
        assert dept["closure_rate"]==50.0
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code.like("S105-%")).delete(synchronize_session=False)
        db.commit()
