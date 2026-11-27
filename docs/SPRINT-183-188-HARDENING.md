# Sprint 183–188 — Migration preflight hardening and task-center governance

## 183 — JSON error normalization
- Make CLI error tests insensitive to message capitalization while preserving structured JSON fields.
- Keep errors informative and avoid exposing connection secrets.

## 184 — Preflight report completeness
- Review report fields for dialect, current revision, target revision, pending count, backup evidence status and explicit migration_applied=false.
- No mutation or migration execution.

## 185 — Compatibility test boundaries
- Define repeatable integration test fixtures for SQLite.
- Document that SQL Server, Oracle, MySQL and PostgreSQL compatibility must be confirmed in dedicated environment tests, not inferred from SQLite.

## 186 — Governance task deduplication design
- Evaluate automated task generators for duplicate/race risks and volume limits.
- Plan a database-backed unique key for source_type/source_id only where semantics permit; avoid destructive migration in this sprint.

## 187 — Task evidence UX
- Plan evidence metadata capture, reviewer, timestamp and link/reference, without storing raw business data or credentials.
- Evidence must not imply independent verification unless performed.

## 188 — Release gate
- Gate on successful CI, reviewed schema migration, authorization checks, backup/restore verification by operators and internal deployment acceptance.
- PR remains draft and unmerged until explicit authorization.

## Safeguards
- Source database connections remain read-only.
- Governance-workbench database mutations require authenticated permission.
- LLM remains optional and off by default; outbound payloads must be redacted.
