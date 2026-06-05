#!/bin/bash
set -e

# Configuration with sensible defaults
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
WORKERS="${WORKERS:-4}"
TIMEOUT="${TIMEOUT:-120}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Prometheus multiprocess mode (required when WORKERS > 1)
if [ "${WORKERS}" -gt 1 ]; then
  export PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus}"
  mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"
  rm -f "${PROMETHEUS_MULTIPROC_DIR}"/*
  echo "Prometheus multiprocess dir: ${PROMETHEUS_MULTIPROC_DIR}"
fi

echo "=========================================="
echo "    Search Proxy - Starting Application   "
echo "=========================================="
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "Workers: ${WORKERS}"
echo "Log Level: ${LOG_LEVEL}"
echo "=========================================="

exec uvicorn \
    unique_search_proxy_client.web.app:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --timeout-keep-alive "${TIMEOUT}" \
    --log-level "${LOG_LEVEL}"
