# Sprint 225–230 — Review audit reliability and governance export hardening

> This is an implementation/acceptance plan, not a statement that the work below is already implemented.

## Baseline observed on PR #44 head
- Review-history endpoint supports offset/limit pagination, up to 200 items per request.
- CSV review-history export currently rejects records beyond 200 instead of providing paged export.
- Integrity endpoint reports orphan task events, missing legacy-record links, and invalid decisions.
- Review records are stored both in a dedicated event model and a legacy Record representation.

## Sprint 225 — Audit integrity report expansion
- Report counts and categorized issues (orphan event, missing legacy reference, duplicate event/legacy representation, invalid decision).
- Keep the report read-only; do not auto-repair links.

## Sprint 226 — Integrity-check pagination and filtering
- Add bounded pagination to integrity checks for large installations.
- Add optional task/date filters where supported by the data model.
- Keep permission requirement governance:read and enforce maximum page size.

## Sprint 227 — Export paging
- Replace the hard 200-record export limitation with a bounded, paginated server-side export strategy.
- Prevent unbounded memory use; document a maximum export size and provide clear errors.
- Preserve CSV BOM and quoting behavior.

## Sprint 228 — Review-history export metadata
- Include export generated timestamp and requested scope in a separate metadata header or clearly defined columns.
- Keep user-entered comments as data; escape CSV safely through csv.writer.

## Sprint 229 — Audit regression tests
- Test pagination boundaries, empty histories, invalid IDs, and filter combinations.
- Test orphan-link integrity classifications without mutating records.
- Test CSV quoting/BOM and export limits.

## Sprint 230 — Acceptance documentation
- Document the integrity report, pagination, export limits, permissions, and operational risks.
- Acceptance requires CI evidence and a review on the PR; this document itself does not constitute verification.

## Safety/operational boundaries
- Read-only inspection; no automatic repair, deletion, or closure of governance tasks.
- Export contents can include user-entered review comments; operators should apply access controls and data minimization.
- Do not treat evidence submission as acceptance or acceptance as proof that source data was remediated.
