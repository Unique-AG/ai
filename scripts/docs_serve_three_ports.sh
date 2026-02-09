#!/usr/bin/env bash
# Run from repo root: ./scripts/docs_serve_three_ports.sh
# Serves root, SDK, and Toolkit on ports 8000, 8001, 8002. No gh-pages, no mike.

set -e
cd "$(git rev-parse --show-toplevel)"

echo "Serving docs on three ports (no gh-pages):"
echo "  Root:    http://127.0.0.1:8000"
echo "  SDK:     http://127.0.0.1:8001"
echo "  Toolkit: http://127.0.0.1:8002"
echo ""
echo "Press Ctrl+C to stop all."
echo ""

trap 'kill $(jobs -p) 2>/dev/null; exit' INT TERM

poetry run mkdocs serve -a 127.0.0.1:8000 &
poetry run mkdocs serve -f unique_sdk/mkdocs.yaml -a 127.0.0.1:8001 &
poetry run mkdocs serve -f unique_toolkit/mkdocs.yaml -a 127.0.0.1:8002 &

wait
