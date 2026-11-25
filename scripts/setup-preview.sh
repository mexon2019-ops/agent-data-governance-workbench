#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "=== Data Governance Workbench V1.0 Preview setup ==="
if [[ ! -f .env ]]; then
  bash scripts/init-preview-env.sh
else
  echo ".env already exists; initializer skipped (no overwrite)."
fi
echo
bash scripts/preflight-preview.sh
echo
echo "Setup/preflight complete. No containers were started."
echo "Review deployment approval and run: bash scripts/deploy-preview.sh"
