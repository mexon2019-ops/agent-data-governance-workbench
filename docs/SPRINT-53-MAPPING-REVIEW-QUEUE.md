# Sprint 53 — Standard mapping review queue

## API
`GET /api/v1/standards/mappings/review-queue`

Query parameters:
- `status`: `待核验` (default), `已落标`, `不符合`, or `全部`
- `standard_id`: optional numeric standard ID
- `limit`: 1–200 (default 100)
- `offset`: zero or greater

Requires `governance:read`. Returns a total count, paging parameters and joined mapping/standard/version/column/table/source context. The endpoint is read-only and does not update source databases or review status.

## Implementation guardrails
- Validate status and paging bounds.
- Order newest mapping records first.
- Only display metadata and mapping notes; no business data rows.
- Review state changes remain through existing write-permission workflows, not this read queue.
