# Sprint 10 — FineReport 11.0 integration foundation

## Scope of this increment
This PR starts a safe, read-only integration track. It adds a conservative SQL dataset
table-reference helper and its tests/documentation. It does **not** connect to the FineReport
server or fetch repository metadata; that requires confirming the 11.0 deployment's
supported API/export interface and a read-only account before the next increment.

## Proposed stages
1. Inventory: report names, folders, identifiers, dataset names, datasource aliases.
2. Extract dataset SQL via a supported FineReport 11.0 interface or administrator export.
3. Analyze SQL into table references and match to existing catalog tables.
4. Show unmapped references, sensitive columns used downstream, and report impact.
5. Extend lineage with report/dataset edges, clearly marking inferred edges and confidence.

## Safety and deployment
- Read-only service account and read-only integration.
- Credentials stored server-side in environment variables/secrets; never in repository or browser.
- Never execute extracted dataset SQL in this integration.
- SQL parsing is heuristic in this foundation; CTEs, dynamic SQL, stored procedures, dialect
  constructs and ambiguous parsing must be flagged for human review.
- FineReport metadata extraction will be version/interface-specific; verify vendor-supported
  interfaces for the deployed 11.0 edition before connecting.
