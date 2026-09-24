"""Dataset-root path and import bootstrap for the account_review FastMCP app."""

from __future__ import annotations

import sys
from pathlib import Path

DATASET_ROOT = Path(__file__).resolve().parent
if str(DATASET_ROOT) not in sys.path:
    sys.path.insert(0, str(DATASET_ROOT))
# Monorepo: .../mcp_dashboards/datasets/account_review/fastmcp → helpers/python/src.
# Docker: /app/dataset — mcp_dashboards is installed via uv; parents[2] does not exist.
if len(DATASET_ROOT.parents) > 2:
    helper_src = DATASET_ROOT.parents[2] / "helpers" / "python" / "src"
    if helper_src.is_dir() and str(helper_src) not in sys.path:
        sys.path.insert(0, str(helper_src))
