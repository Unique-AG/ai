#!/usr/bin/env bash
# Runs pytest with coverage and reports uncovered lines.
# Usage: ./scripts/analyze_coverage.sh [src_dir]
set -euo pipefail
SRC=${1:-src}
pytest --cov="$SRC" --cov-report=term-missing -q
