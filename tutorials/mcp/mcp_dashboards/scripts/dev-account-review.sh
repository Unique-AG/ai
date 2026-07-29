#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_SERVER="$ROOT/datasets/account_review/fastmcp/server.py"
ASTRO_DIR="$ROOT/datasets/account_review/astro"

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}

trap cleanup EXIT INT TERM

echo "Starting account_review FastMCP server..."
uv run --project "$ROOT/helpers/python" python "$MCP_SERVER" &
PIDS+=("$!")

echo "Starting account_review Astro dashboard..."
npm --prefix "$ASTRO_DIR" run dev:live-local &
PIDS+=("$!")

while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      wait "$pid"
      exit $?
    fi
  done
  sleep 1
done
