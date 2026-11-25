#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo "=== Docker / Compose ==="
docker --version 2>&1 || true
docker compose version 2>&1 || true
echo "=== Compose config validation ==="
docker compose config --quiet 2>&1 || true
echo "=== Service state ==="
docker compose ps 2>&1 || true
echo "=== Host storage ==="
df -h . 2>&1 || true
echo "=== Docker storage ==="
docker system df 2>&1 || true
echo "=== Recent service log summary (redacted) ==="
# Redact common credentials/token patterns before showing log lines.
docker compose logs --tail=80 2>&1 | sed -E 's/(password|passwd|secret|token|api[_-]?key)([=: ]+)[^ ]+/\1\2[REDACTED]/Ig'
echo "Diagnosis output may still contain sensitive information; review before sharing."
