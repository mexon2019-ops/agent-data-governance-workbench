#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
fail=0
warn(){ echo "WARN: $*"; }
check(){ echo "PASS: $*"; }
command -v docker >/dev/null || { echo "FAIL: Docker missing"; exit 1; }
docker compose version >/dev/null || { echo "FAIL: Docker Compose V2 missing"; exit 1; }
[[ -f .env ]] || { echo "FAIL: .env missing; cp .env.example .env and configure it"; exit 1; }
chmod 600 .env
if [[ "$(uname -s)" != Linux ]]; then warn "Deployment target is documented for Linux; current host is $(uname -s)."; fi
for key in POSTGRES_PASSWORD AUTH_SECRET BOOTSTRAP_ADMIN_PASSWORD MYSQL_TEST_ROOT_PASSWORD MYSQL_TEST_READER_PASSWORD; do
 value="$(awk -F= -v key="$key" '$1==key {sub(/^[^=]*=/,""); print; exit}' .env | tr -d '\r')"
 if [[ -z "$value" || "$value" == *"replace-with"* || "$value" == *"change-this"* ]]; then echo "FAIL: $key is unset or placeholder"; fail=1; fi
done
auth="$(awk -F= '$1=="AUTH_SECRET" {sub(/^[^=]*=/,"");print;exit}' .env)"
admin="$(awk -F= '$1=="BOOTSTRAP_ADMIN_PASSWORD" {sub(/^[^=]*=/,"");print;exit}' .env)"
[[ ${#auth} -ge 32 ]] || { echo "FAIL: AUTH_SECRET must be >=32 chars"; fail=1; }
[[ ${#admin} -ge 16 ]] || { echo "FAIL: BOOTSTRAP_ADMIN_PASSWORD must be >=16 chars"; fail=1; }
avail_kb="$(df -Pk . | awk 'NR==2 {print $4}')"
if [[ -n "$avail_kb" && "$avail_kb" -lt 10485760 ]]; then warn "Less than 10 GiB available disk space."; else check "disk space threshold (10 GiB)"; fi
if command -v ss >/dev/null; then
 for port in 8000 8080; do
  if ss -ltn | awk '{print $4}' | grep -Eq "(:|])$port$"; then echo "WARN: TCP port $port appears occupied"; else check "TCP port $port appears free"; fi
 done
else warn "ss unavailable; port occupancy check skipped"; fi
docker compose config --quiet || fail=1
docker compose --profile mysql-test config --quiet || fail=1
[[ "$fail" -eq 0 ]] || { echo "Preflight FAILED; fix items above."; exit 1; }
check "Compose configuration and secrets checks"
echo "Preflight passed. This script does not deploy containers."
