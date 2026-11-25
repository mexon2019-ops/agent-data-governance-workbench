#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ -e .env ]]; then
  echo "Refusing to overwrite existing .env. Back it up and edit manually if needed."
  exit 1
fi
command -v openssl >/dev/null || { echo "FAIL: openssl is required"; exit 1; }
[[ -f .env.example ]] || { echo "FAIL: .env.example missing"; exit 1; }
cp .env.example .env
# Generate unique secrets for database and application signing.
set_value(){ local key="$1" value="$2" escaped; escaped="${value//\\/\\\\}"; escaped="${escaped//&/\\&}"; escaped="${escaped//|/\\|}"; sed -i "s|^${key}=.*|${key}=${escaped}|" .env; }
set_value POSTGRES_PASSWORD "$(openssl rand -hex 32)"
set_value MYSQL_TEST_ROOT_PASSWORD "$(openssl rand -hex 32)"
set_value MYSQL_TEST_READER_PASSWORD "$(openssl rand -hex 32)"
set_value AUTH_SECRET "$(openssl rand -hex 32)"
read -r -s -p "Set bootstrap administrator password (>=16 characters): " admin
echo
if [[ ${#admin} -lt 16 || "$admin" == *"|"* || "$admin" == *$"\\n"* ]]; then echo "FAIL: password must be at least 16 characters and must not contain | or newlines"; rm -f .env; exit 1; fi
set_value BOOTSTRAP_ADMIN_PASSWORD "$admin"
unset admin
chmod 600 .env
echo ".env initialized with generated secrets and mode 600."
echo "Review .env locally; keep LLM_EXTERNAL_ENABLED=false and do not commit it."
echo "Next: bash scripts/preflight-preview.sh"
