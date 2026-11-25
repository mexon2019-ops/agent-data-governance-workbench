# Governance trends API recovery

- Read-only endpoint: GET /api/v1/governance/trends
- Requires governance:read permission.
- Rolling 12 calendar-month counts for governance issues created and closed.
- Aggregates only governance issue timestamps; no source data access, writes, migrations, or external LLM calls.
- Historical state transitions are not reconstructed.
