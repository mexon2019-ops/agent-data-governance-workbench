import os, uuid, json
os.environ.setdefault("DATABASE_URL",f"sqlite:////tmp/sprint243-detail-{uuid.uuid4().hex}.db")
os.environ.setdefault("AUTH_SECRET","test-only-secret-that-is-long-enough-for-ci-123456")
from app import main

def test_action_history_and_legacy_detail():
    main.Base.metadata.create_all(main.engine)
    user=main.User(username="s243-"+uuid.uuid4().hex[:6],password_hash="test")
    legacy=main.Record(category="task_review",name="review fixture",description=json.dumps({"task_id":7,"decision":"通过","comment":"fixture"}),status="记录",owner="reviewer")
    with main.SessionLocal() as db:
        db.add_all([user,legacy]);db.commit();db.refresh(legacy)
        detail=main.review_integrity_detail(category="malformed_legacy_record",record_id=legacy.id,_user=None,db=db)
        assert detail["resolved"] is True and detail["payload"]["decision"]=="通过"
        created=main.create_review_integrity_action(main.ReviewIntegrityActionIn(issue_category="malformed_legacy_record",issue_record_id=legacy.id,status="处理中",note="核查"),user=user,db=db)
        updated=main.create_review_integrity_action(main.ReviewIntegrityActionIn(issue_category="malformed_legacy_record",issue_record_id=legacy.id,status="已解决",note="完成"),user=user,db=db)
        history=main.review_integrity_action_history(category="malformed_legacy_record",record_id=legacy.id,_user=None,db=db)
        assert created["id"]==updated["id"]
        assert len(history["history"])==2
        assert history["history"][-1]["status"]=="已解决"
        db.delete(db.get(main.Record,created["id"]));db.delete(legacy);db.delete(user);db.commit()
