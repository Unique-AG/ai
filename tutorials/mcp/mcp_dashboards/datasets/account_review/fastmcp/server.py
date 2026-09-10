"""Backward-compatible entrypoint for the account_review FastMCP app.

Prefer ``app.py``. This module re-exports the same public surface so existing
scripts that import ``server.py`` keep working.
"""

from __future__ import annotations

import paths as _paths  # noqa: F401 — dataset root + helpers on sys.path
from app import *  # noqa: F403
from app import main

if __name__ == "__main__":
    main()
