# Sprint 18 — Governance Operations Dashboard

## Scope
- Add dashboard summary for governance issue closure, overdue count and status distribution.
- Show quality-run success/failure counts and recent issue list.
- Keep existing asset/standard/rule cards and roadmap.
- API GET /api/v1/governance/overview requires governance:read.

## Safety
- Uses governance issue and quality-run metadata only; does not read source business rows or mutate issues.

## Validation
- GitHub Actions/runtime validation pending. Confirm model attribute compatibility, endpoint authorization and frontend build before merge.
