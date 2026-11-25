# Sprint 29–32 platform consolidation

## Sprint 29 — Integration/stability checkpoint
- Branch dependency documented: PR #33 API layer precedes PR #34 analytics UI.
- Legacy PR #29 and #31 remain separately reviewable; do not merge without conflict and duplicate-route review.
- This sprint branch is stacked on PR #34 and cannot safely be merged to main before dependency integration.

## Sprint 30 — Consolidated governance dashboard
- Add 12-month monthly created/closed governance issue trend table to dashboard.
- Existing overview and maturity summary remain visible.
- Trend series displays monthly counts and net change.

## Sprint 31 — Task operations
- Add status and department filters to governance task inventory.
- Keep advisory priority ranking separate from manual assignment/remediation workflow.

## Sprint 32 — Agent reporting
- Add prompt shortcuts for governance risk diagnosis and monthly governance operations report.
- Existing Agent endpoint only receives aggregate governance counters and prompt text; external-model use remains explicit opt-in.
- Suggestions are not automatically executed or assigned.

## Integration caveat
- PR #33 and #34 require integration first; no automatic merge or deployment performed here.
- CI/runtime tests should be run after stack is rebased/retargeted.
