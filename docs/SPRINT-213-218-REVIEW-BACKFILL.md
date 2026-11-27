# Sprint 213–218: Legacy review-event backfill safety

- Added a dry-run-first backfill utility.
- Valid decisions are only `通过` and `退回`.
- Malformed JSON, unsupported decisions, and task IDs that do not resolve to an existing task are skipped and counted.
- Backfill uses `legacy_record_id` as an idempotency key.
- Default invocation prints planned counts and makes no changes.
- `--apply` persists only after operator review and backup.
- No production DB operation was performed by this development increment.

Run from backend:
```bash
python scripts/backfill_governance_review_events.py
python scripts/backfill_governance_review_events.py --apply
```
