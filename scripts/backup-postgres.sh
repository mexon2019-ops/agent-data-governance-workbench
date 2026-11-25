#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f .env ]] || { echo "ERROR: .env not found"; exit 1; }
docker compose exec -T postgres pg_isready -U dg_user -d data_governance >/dev/null
backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
stamp="$(date +%Y%m%d-%H%M%S)"
file="$backup_dir/data_governance-$stamp.sql.gz"
tmp="$(mktemp "$backup_dir/.backup-$stamp-XXXXXX")"
cleanup(){ rm -f "$tmp"; }
trap cleanup EXIT
docker compose exec -T postgres pg_dump -U dg_user -d data_governance --no-owner --no-privileges | gzip -c > "$tmp"
[[ -s "$tmp" ]] || { echo "ERROR: backup file empty" >&2; exit 1; }
gzip -t "$tmp"
chmod 600 "$tmp"
mv "$tmp" "$file"
trap - EXIT
echo "Backup created and gzip integrity checked: $file"
echo "IMPORTANT: restoration testing is still required; store a copy in a separate protected location."
