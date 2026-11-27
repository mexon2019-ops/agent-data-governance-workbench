# Sprint 48–52: asset and standards foundations

## Scope and delivery sequence
- **48 Asset detail foundation:** align the table-level asset record with its metadata table and provide an asset detail context (physical metadata, ownership, business description, tags, lifecycle, sensitivity).
- **49 Ownership and stewardship:** clarify owner/department, tag conventions, business-domain vocabulary, and asset review checklist; avoid duplicating existing asset CRUD.
- **50 Classification workflow:** improve field classification reviewability and evidence (classification basis, reviewer, date); suggestions remain advisory and must be confirmed by an authorized user.
- **51 Standards lifecycle:** standard definitions, owner/domain, versions, publish lifecycle, effective date and change governance; preserve existing version lifecycle APIs.
- **52 Field mapping:** map standard versions to metadata columns, track mapping status and notes. Batch mapping is bounded (up to 500), rejects duplicate column IDs in a request and upserts existing mappings.

## Sprint 52 API increment
`POST /api/v1/standards/{standard_id}/versions/{version_id}/mappings/bulk`

Request:
```json
{
  "mappings": [
    {"metadata_column_id": 12, "mapping_status": "已落标", "note": "reviewed"},
    {"metadata_column_id": 13, "mapping_status": "待核验", "note": ""}
  ]
}
```

- 1–500 mappings per request.
- Valid states: `待核验`, `已落标`, `不符合`.
- Existing mapping for the same standard version and column is updated; otherwise created.
- Duplicate field IDs in a single request are rejected.
- No source database writes are performed.
- Requires `governance:write`.

## Validation
Automated tests cover batch create/update and mapping detail visibility. CI and the complete test suite remain the authoritative validation after PR creation.

## Acceptance criteria for the five-sprint work package
1. Assets expose usable business description, ownership, domain, tags and lifecycle information, with edits auditable.
2. Classification recommendations are visibly advisory and confirmed classifications retain evidence.
3. Standards support versioned definitions and explicit publication state.
4. A standard version can map multiple catalog columns with review status and notes.
5. Mapping appears consistently in standard detail and metadata-column detail.
6. No governance action implicitly writes to source databases.
