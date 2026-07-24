#!/bin/bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# dep-tree cannot resolve `from mcp_sqlite_excel import prompts` under a src/
# layout, so pass every local module as an entrypoint to include orphan nodes.
ENTRYPOINTS=()
while IFS= read -r f; do
    ENTRYPOINTS+=("$f")
done < <(find "${ROOT}/src/mcp_sqlite_excel" -name '*.py' | sort)

PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}" uv run dep-tree entropy \
    "${ENTRYPOINTS[@]}" \
    --render-path "${ROOT}/data/dep_graph.html" \
    --python-exclude-conditional-imports
