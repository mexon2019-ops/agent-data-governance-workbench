#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then echo ".env missing; copy .env.example and configure secrets." >&2; exit 1; fi
chmod 600 .env
# Avoid sourcing .env as shell code; inspect required values as text.
for name in MYSQL_TEST_ROOT_PASSWORD MYSQL_TEST_READER_PASSWORD; do
 value="$(awk -F= -v key="$name" '$1==key {sub(/^[^=]*=/,""); print; exit}' .env | tr -d '\r')"
 if [[ -z "$value" || "$value" == *"change-this"* || "$value" == *"replace-with"* ]]; then echo "Set non-placeholder $name in .env." >&2; exit 1; fi
done
docker compose --profile mysql-test config --quiet
echo "Starts isolated synthetic MES test database on host port 3307; no production DB is touched."
read -r -p "Proceed? Type START: " answer
[[ "$answer" == "START" ]] || { echo "Cancelled."; exit 0; }
docker compose --profile mysql-test up -d mysql-test
echo "Waiting up to 120 seconds for health..."
for i in $(seq 1 60); do
 cid="$(docker compose --profile mysql-test ps -q mysql-test)"
 if [[ -n "$cid" ]]; then
  health="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || true)"
  if [[ "$health" == "healthy" ]]; then
   echo "Healthy: host 127.0.0.1 port 3307, database mes_test, user metadata_reader."
   echo "Reader password: local .env MYSQL_TEST_READER_PASSWORD"
   exit 0
  fi
 fi
 sleep 2
done
echo "Timeout. Run bash scripts/diagnose.sh; inspect mysql-test logs locally." >&2
exit 1
