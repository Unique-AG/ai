#!/usr/bin/env bash
# Run deploy.sh with secrets injected by SecretSpec (1Password).
# Pulls secretspec from nixpkgs when it is not already on PATH — no profile install.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REASON="${SECRETSPEC_REASON:-Deploy account-review MCP}"

run_deploy() {
  exec secretspec run --profile deploy --reason "$REASON" -- ./deploy.sh "$@"
}

if command -v secretspec >/dev/null 2>&1; then
  run_deploy "$@"
fi

if command -v nix >/dev/null 2>&1; then
  echo "secretspec not on PATH — using nix shell nixpkgs#secretspec…"
  exec nix shell nixpkgs#secretspec -c secretspec run --profile deploy --reason "$REASON" -- ./deploy.sh "$@"
fi

echo "ERROR: secretspec not on PATH and nix is unavailable."
echo "  nix-shell                 # uses shell.nix"
echo "  direnv allow              # after installing direnv"
exit 1
