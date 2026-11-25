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
echo "=== Recent log availability (not printing log contents) ==="
for svc in postgres backend frontend; do
  if docker compose ps --services 2>/dev/null | grep -Fxq "$svc"; then
    echo "$svc: service is defined; inspect locally with: docker compose logs --tail=80 $svc"
  else echo "$svc: not found in Compose service list"; fi
done
echo "Logs may contain sensitive information. Inspect locally and redact before sharing."
