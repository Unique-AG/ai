#!/usr/bin/env bash
# Run deploy.sh with secrets injected by SecretSpec (1Password).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v secretspec >/dev/null 2>&1; then
  echo "ERROR: secretspec not on PATH."
  exit 1
fi

REASON="${SECRETSPEC_REASON:-Deploy account-review MCP}"
exec secretspec run --profile deploy --reason "$REASON" -- ./deploy.sh "$@"
