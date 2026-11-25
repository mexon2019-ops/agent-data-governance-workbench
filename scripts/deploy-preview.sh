#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
command -v docker >/dev/null || { echo "ERROR: Docker not installed"; exit 1; }
docker compose version >/dev/null || { echo "ERROR: Docker Compose plugin unavailable"; exit 1; }
[[ -f .env ]] || { echo "ERROR: .env missing; copy .env.example and configure"; exit 1; }
chmod 600 .env
required=(POSTGRES_PASSWORD AUTH_SECRET BOOTSTRAP_ADMIN_PASSWORD MYSQL_TEST_ROOT_PASSWORD MYSQL_TEST_READER_PASSWORD)
for key in "${required[@]}"; do
  value="$(grep -E "^(${key})=" .env | tail -1 | cut -d= -f2- || true)"
  [[ -n "$value" ]] || { echo "ERROR: ${key} is empty in .env"; exit 1; }
  case "$value" in *replace-with*|*change-this*) echo "ERROR: ${key} still contains placeholder value"; exit 1;; esac
done
auth="$(grep '^AUTH_SECRET=' .env | cut -d= -f2-)"
admin="$(grep '^BOOTSTRAP_ADMIN_PASSWORD=' .env | cut -d= -f2-)"
[[ ${#auth} -ge 32 ]] || { echo "ERROR: AUTH_SECRET must be at least 32 characters"; exit 1; }
[[ ${#admin} -ge 16 ]] || { echo "ERROR: BOOTSTRAP_ADMIN_PASSWORD must be at least 16 characters"; exit 1; }
docker compose config --quiet
echo "Configuration preflight passed. Review .env and server/network settings before proceeding."
read -r -p "Start/upgrade V1.0 Preview containers now? [y/N] " answer
[[ "$answer" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }
docker compose up -d --build
echo "Deployment command completed. Run scripts/health-check.sh to verify."
