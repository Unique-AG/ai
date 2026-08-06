#!/usr/bin/env python3
"""Dump mock-mode JSON fixtures straight from the real dataset.

Why this exists
----------------
Every live binding in this dashboard queries typed account-review tools. Rather
than hand-authoring mock fixtures that drift from the TypeSpec contract, this
script dumps the typed ``Client`` objects produced by the real server helpers.

``public/mock-host.js`` then re-derives each list's rows at runtime by
applying that list's own ``data-unique-source-args`` against this one typed
array, so mutations made through the mock UI stay consistent across every list
bound to ``clients``, exactly like the real backend.

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
DATASET_ROOT = ASTRO_ROOT.parent
PROJECT_ROOT = DATASET_ROOT.parents[1]
HELPER_SRC = PROJECT_ROOT / "helpers" / "python" / "src"
FASTMCP_ROOT = DATASET_ROOT / "fastmcp"
sys.path.insert(0, str(HELPER_SRC))
sys.path.insert(0, str(FASTMCP_ROOT))

from mcp_dashboards.binding import enrich_binding_row  # noqa: E402
from mcp_dashboards.settings import AppSettings  # noqa: E402
from server import _clients_from_rows, repo  # noqa: E402

EXCEL_PATH = DATASET_ROOT / "fastmcp" / "data" / "account_review_dataset.xlsx"
SQLITE_PATH = DATASET_ROOT / "fastmcp" / "data" / "account_review.sqlite"
COMBINED_OUT = ASTRO_ROOT / "src" / "data" / "mock.json"

# Every table referenced by any data-unique-source-args in src/pages/index.astro.
TABLES = ["clients"]


def main() -> None:
    if not EXCEL_PATH.is_file():
        raise SystemExit(
            f"Missing {EXCEL_PATH} - restore the account-review Excel fixture first."
        )

    repo.settings = AppSettings(excel_path=EXCEL_PATH, sqlite_path=SQLITE_PATH)
    repo.excel_path = EXCEL_PATH
    repo.db_path = SQLITE_PATH
    repo.invalidate_schema_cache()
    repo.ensure_ready()

    fixtures: dict[str, list[dict]] = {}
    for table in TABLES:
        result = repo.list_rows(table, limit=100_000)
        fixtures[table] = [
            enrich_binding_row(client.model_dump(mode="json"))
            for client in _clients_from_rows(result.rows)
        ]

    COMBINED_OUT.parent.mkdir(parents=True, exist_ok=True)
    COMBINED_OUT.write_text(json.dumps(fixtures, indent=2) + "\n")

    for table, rows in fixtures.items():
        print(f"  {table:<10} {len(rows):>3} rows")
    print(f"wrote {COMBINED_OUT.relative_to(ASTRO_ROOT)}")


if __name__ == "__main__":
    main()
