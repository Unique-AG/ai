#!/bin/bash
set -e

# Configuration with sensible defaults
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-4}"
TIMEOUT="${TIMEOUT:-120}"
LOG_LEVEL="${LOG_LEVEL:-info}"

echo "=========================================="
echo "            🧪 EXPERIMENTAL 🧪            "
echo "    Search Proxy - Starting Application   "
echo "=========================================="
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "Workers: ${WORKERS}"
echo "Log Level: ${LOG_LEVEL}"
echo "=========================================="

# Execute the main process (replaces shell, proper signal handling)
exec poetry run uvicorn \
    app:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --timeout-keep-alive "${TIMEOUT}" \
    --log-level "${LOG_LEVEL}"
