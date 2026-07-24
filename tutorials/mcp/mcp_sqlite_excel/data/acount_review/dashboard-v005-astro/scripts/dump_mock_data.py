#!/usr/bin/env python3
"""Dump mock-mode JSON fixtures straight from the real dataset.

Why this exists
----------------
Every live binding in this dashboard (``list_rows``/``count_by`` calls, see
``src/pages/index.astro``) queries one table: ``clients``. Rather than
hand-authoring separate mock fixtures per list id (which drift from the real
schema the moment a column is renamed, and can't reflect writes consistently
across lists), this script dumps the *whole* table once, verbatim, using the
same ``SqliteCrudRepository`` the live MCP server uses, against the real
``account_review_dataset.xlsx``.

``public/mock-host.js`` then re-derives each list's rows at runtime by
applying that list's own ``data-unique-source-args`` (filters/limit for
``list_rows``, grouping for ``count_by``) against this one table — a tiny
client-side re-implementation of ``repository.list_rows``/``count_by`` — so
mutations (escalate/update) made through the mock UI stay consistent across
every list bound to ``clients``, exactly like the real backend.

Usage
-----
    uv run python scripts/dump_mock_data.py

Writes ``src/data/mock.json``: ``{"clients": [...]}``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ASTRO_ROOT = Path(__file__).resolve().parent.parent
MCP_ROOT = ASTRO_ROOT.parents[2]  # tutorials/mcp/mcp_sqlite_excel
sys.path.insert(0, str(MCP_ROOT / "src"))

from mcp_sqlite_excel.db.repository import SqliteCrudRepository  # noqa: E402
from mcp_sqlite_excel.settings import AppSettings  # noqa: E402

EXCEL_PATH = MCP_ROOT / "data" / "account_review_dataset.xlsx"
SQLITE_PATH = MCP_ROOT / "data" / "portfolio.db"
COMBINED_OUT = ASTRO_ROOT / "src" / "data" / "mock.json"

# Every table referenced by any data-unique-source-args in src/pages/index.astro.
TABLES = ["clients"]


def main() -> None:
    if not EXCEL_PATH.is_file():
        raise SystemExit(
            f"Missing {EXCEL_PATH} — this spike reuses the real account-review "
            "dataset for mock data; generate/restore it first."
        )

    settings = AppSettings(excel_path=EXCEL_PATH, sqlite_path=SQLITE_PATH, auth_disabled=True)
    repo = SqliteCrudRepository(settings=settings)
    repo.ensure_ready()

    fixtures: dict[str, list[dict]] = {}
    for table in TABLES:
        fixtures[table] = repo.list_rows(table, limit=100_000).rows

    COMBINED_OUT.parent.mkdir(parents=True, exist_ok=True)
    COMBINED_OUT.write_text(json.dumps(fixtures, indent=2) + "\n")

    for table, rows in fixtures.items():
        print(f"  {table:<10} {len(rows):>3} rows")
    print(f"→ {COMBINED_OUT.relative_to(ASTRO_ROOT)}")


if __name__ == "__main__":
    main()
