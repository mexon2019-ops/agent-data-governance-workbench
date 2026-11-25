# Sprints 25–28 — Governance operations UI

## Sprint 25
- Added a dedicated Governance Analytics navigation page.
- Connects standard coverage, quality analytics, classification analytics and advisory priority APIs.
- Shows domain rollups, capped unmapped/unclassified inventories and quality rule summaries.

## Sprint 26
- Integrates advisory priorities into the governance task workflow view (priorities loaded alongside the issue list).
- Existing issue workflow remains responsible for manual assignment, remediation, recheck and closure.
- Priorities are advisory only.

## Sprint 27
- Dashboard requests the monthly trend series.
- Analytics page includes the rolling monthly issue trend table and consolidated governance analysis sections.

## Sprint 28
- Analytics UI uses explicit API-derived metrics and inventories for human review; no external model call or automatic remediation.
- Access is governed by existing authenticated UI and API permissions.
