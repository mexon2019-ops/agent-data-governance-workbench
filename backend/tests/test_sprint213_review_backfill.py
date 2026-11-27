import json
from app import main
from scripts.backfill_governance_review_events import plan_backfill, apply_plan


def test_backfill_plan_is_dry_and_idempotent():
    main.Base.metadata.create_all(main.engine)
    with main.SessionLocal() as db:
        task=main.GovernanceTask(task_code="S213-BACKFILL",title="Backfill fixture")
        db.add(task);db.commit();db.refresh(task)
        row=main.Record(category="task_review",name="legacy",description=json.dumps({"task_id":task.id,"decision":"退回","reviewer":"reviewer","comment":"fixture"}),owner="reviewer")
        db.add(row);db.commit();db.refresh(row)
        record_id=row.id
        planned=plan_backfill(db)
        matches=[x for x in planned["plan"] if x["legacy_record_id"]==record_id]
        assert len(matches)==1
        # Planning is non-mutating.
        assert db.query(main.GovernanceReviewEvent).filter_by(legacy_record_id=record_id).count()==0
        inserted=apply_plan(db,matches)
        assert inserted==1
        second=plan_backfill(db)
        assert record_id not in [x["legacy_record_id"] for x in second["plan"]]
        db.query(main.GovernanceReviewEvent).filter_by(legacy_record_id=record_id).delete()
        db.delete(row);db.delete(task);db.commit()
