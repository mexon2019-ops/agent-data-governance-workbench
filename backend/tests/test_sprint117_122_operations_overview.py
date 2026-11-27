import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/sprint117-122-overview-test.db")
os.environ.setdefault("AUTH_SECRET", "test-only-secret-that-is-long-enough-for-ci-123456")
from app import main


def test_operations_overview_aggregates_counts():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code.like("S117-%")).delete(synchronize_session=False)
        db.add_all([
            main.GovernanceTask(task_code="S117-A",title="安全整改",source_type="asset_checklist",owner_department="数据部",owner="",status="待处理"),
            main.GovernanceTask(task_code="S117-B",title="常规任务",source_type="manual",owner_department="数据部",owner="user",status="已关闭"),
        ])
        db.commit()
        user=type("UserFixture",(),{"username":"fixture"})()
        result=main.governance_tasks_operations_overview(_user=user,db=db)
        assert result["total"]>=2
        assert result["by_source"]["asset_checklist"]>=1
        assert result["by_status"]["已关闭"]>=1
        assert result["by_priority"]["高"]>=1
        assert sum(result["aging_buckets"].values())==result["total"]
        db.query(main.GovernanceTask).filter(main.GovernanceTask.task_code.like("S117-%")).delete(synchronize_session=False)
        db.commit()
