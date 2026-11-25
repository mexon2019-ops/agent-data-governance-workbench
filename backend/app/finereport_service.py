"""Conservative SQL table-reference extraction for report dataset lineage.

This helper intentionally does not claim full SQL parsing. It extracts simple FROM/JOIN
references and skips subqueries/CTEs and ambiguous constructs for manual review.
"""
import re
from typing import Any

_IDENT = r"(?:\[[^\]]+\]|\`[^\`]+\`|\"[^\"]+\"|[A-Za-z_][\w$]*)"
_TABLE = re.compile(r"(?is)\b(?:FROM|JOIN)\s+(" + _IDENT + r"(?:\s*\.\s*" + _IDENT + r"){0,2})")

def _unquote(part: str) -> str:
    part = part.strip()
    if part.startswith("[") and part.endswith("]"):
        return part[1:-1]
    if part.startswith("`") and part.endswith("`"):
        return part[1:-1]
    if part.startswith('"') and part.endswith('"'):
        return part[1:-1]
    return part

def extract_sql_table_references(sql: str) -> dict[str, Any]:
    """Return normalized table references and a review flag; no SQL is executed."""
    if not isinstance(sql, str) or not sql.strip():
        return {"tables": [], "review_required": True, "reason": "empty SQL"}
    # Remove comments and quoted string literals to reduce false positives.
    cleaned = re.sub(r"--[^\\n]*|/\\*.*?\\*/", " ", sql, flags=re.S)
    cleaned = re.sub(r"'(?:''|[^'])*'", "''", cleaned)
    refs = []
    for match in _TABLE.finditer(cleaned):
        raw = match.group(1)
        parts = [_unquote(p.strip()) for p in re.split(r"\s*\.\s*", raw)]
        if any(p.lower() in {"select", "values"} for p in parts):
            continue
        ref = ".".join(parts)
        if ref not in refs:
            refs.append(ref)
    has_cte = bool(re.search(r"(?is)^\s*WITH\b", cleaned))
    return {
        "tables": refs,
        "review_required": has_cte or not refs,
        "reason": "CTE or unresolved syntax requires manual review" if has_cte or not refs else "",
    }
