"""Idempotent, dry-run-first backfill of legacy governance review Records."""
import argparse
import json
from sqlalchemy import select
from app.main import SessionLocal, Record, GovernanceTask, GovernanceReviewEvent


def plan_backfill(db):
    legacy=db.scalars(select(Record).where(Record.category=="task_review").order_by(Record.id)).all()
    existing_ids=set(db.scalars(select(GovernanceReviewEvent.legacy_record_id).where(GovernanceReviewEvent.legacy_record_id.is_not(None))).all())
    task_ids=set(db.scalars(select(GovernanceTask.id)).all())
    plan=[]; malformed=0; invalid=0; orphan=0; already=0
    for row in legacy:
        if row.id in existing_ids:
            already+=1; continue
        try: payload=json.loads(row.description or "{}")
        except (TypeError,json.JSONDecodeError):
            malformed+=1; continue
        tid=payload.get("task_id"); decision=payload.get("decision")
        if not isinstance(tid,int) or tid not in task_ids:
            orphan+=1; continue
        if decision not in ("通过","退回"):
            invalid+=1; continue
        plan.append({"task_id":tid,"reviewer":payload.get("reviewer") or row.owner or "",
                     "decision":decision,"comment":payload.get("comment") or "",
                     "legacy_record_id":row.id,"created_at":row.created_at})
    return {"plan":plan,"malformed":malformed,"invalid":invalid,"orphan":orphan,"already":already}


def apply_plan(db, plan):
    inserted=0
    for item in plan:
        if db.scalar(select(GovernanceReviewEvent.id).where(GovernanceReviewEvent.legacy_record_id==item["legacy_record_id"])) is not None:
            continue
        db.add(GovernanceReviewEvent(**item)); inserted+=1
    db.commit()
    return inserted


def main_cli():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true",help="persist the planned backfill; default is dry run")
    args=parser.parse_args()
    with SessionLocal() as db:
        result=plan_backfill(db)
        print(json.dumps({k:v for k,v in result.items() if k!="plan"} | {"planned":len(result["plan"])},ensure_ascii=False,indent=2))
        if args.apply:
            inserted=apply_plan(db,result["plan"])
            print(json.dumps({"applied":inserted},ensure_ascii=False))
        else:
            print("DRY RUN: no data changed; use --apply only after backup and review.")


if __name__=="__main__":
    main_cli()
