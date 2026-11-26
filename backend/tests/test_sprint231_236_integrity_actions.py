import os, uuid, json
os.environ.setdefault("DATABASE_URL",f"sqlite:////tmp/sprint231-actions-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET","test-only-secret-that-is-long-enough-for-ci-123456")
from app import main

def test_integrity_action_create_update_summary():
    main.Base.metadata.create_all(main.engine)
    user=main.User(username="s231-"+uuid.uuid4().hex[:6],password_hash="test")
    with main.SessionLocal() as db:
        db.add(user);db.commit()
        payload=main.ReviewIntegrityActionIn(issue_category="orphan_task_event",issue_record_id=101,status="处理中",note="人工核查")
        created=main.create_review_integrity_action(payload,user=user,db=db)
        assert created["status"]=="处理中"
        updated=main.create_review_integrity_action(main.ReviewIntegrityActionIn(issue_category="orphan_task_event",issue_record_id=101,status="已解决",note="已确认处理"),user=user,db=db)
        assert updated["id"]==created["id"] and updated["status"]=="已解决"
        summary=main.review_integrity_action_summary(_user=None,db=db)
        assert summary["summary"]["total"]>=1 and summary["summary"]["已解决"]>=1
        row=db.get(main.Record,created["id"]);db.delete(row);db.delete(user);db.commit()
