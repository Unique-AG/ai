#!/usr/bin/env bash
# Run every Entangled doc example against workspace packages (not PyPI).
#
# Usage (from repo root; unique.env in repo root or ENVIRONMENT_FILE_PATH set):
#   unique_toolkit/scripts/run_all_doc_examples.sh
#
# SSE/chat examples block until an event arrives. Expect failures without a live tenant.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
EXAMPLES="${REPO_ROOT}/unique_toolkit/docs/examples_from_docs"
WITH=(
  --no-project
  --with "unique-sdk @ file://${REPO_ROOT}/unique_sdk"
  --with "unique-toolkit @ file://${REPO_ROOT}/unique_toolkit"
)

failures=()
for script in "${EXAMPLES}"/*.py; do
  if [[ ! -f "$script" ]]; then
    continue
  fi
  name="$(basename "$script")"
  run_cmd=(uv run "${WITH[@]}")
  if [[ "$name" == langchain_* ]]; then
    run_cmd+=(--with "unique-toolkit[langchain] @ file://${REPO_ROOT}/unique_toolkit")
  fi
  run_cmd+=("$script")
  echo "=== ${name} ==="
  if ! "${run_cmd[@]}"; then
    failures+=("$name")
  fi
done

if [[ ${#failures[@]} -gt 0 ]]; then
  printf 'Failed (%d): %s\n' "${#failures[@]}" "${failures[*]}"
  exit 1
fi

echo "All examples completed successfully."
