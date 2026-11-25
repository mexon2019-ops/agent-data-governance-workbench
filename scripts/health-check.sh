#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
fail=0
command -v docker >/dev/null || { echo "FAIL: Docker not found"; exit 1; }
docker compose ps
for svc in postgres backend frontend; do
  state="$(docker compose ps --status running --services 2>/dev/null | grep -Fx "$svc" || true)"
  if [[ "$state" == "$svc" ]]; then echo "PASS: $svc running"; else echo "FAIL: $svc not running"; fail=1; fi
done
if command -v curl >/dev/null; then
  for target in "http://127.0.0.1:8000/docs" "http://127.0.0.1:8080/"; do
    if curl -fsS --max-time 8 "$target" >/dev/null; then echo "PASS: HTTP $target"; else echo "FAIL: HTTP $target"; fail=1; fi
  done
else echo "WARN: curl unavailable; skipped HTTP probes"; fi
exit "$fail"
