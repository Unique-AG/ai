"""Agentic Table (magic table) read commands for the Unique CLI.

Tier 0 reads over the public magic-table API (``2023-12-06``): fetch a sheet
summary, a single cell, or a cell's edit history. Every call is scoped to the
runner-injected user/company; sheet-role enforcement (Owner / Can manage /
Can edit) happens server-side via the platform's access guard, and a 403 is
surfaced as ``agentic-table: permission denied``.

These reads require no confirmation. Later write commands live in their own
module so the audit/activity-status plumbing lands with its first caller.
"""

from __future__ import annotations

import asyncio
import json

from unique_sdk._error import UniqueError
from unique_sdk.api_resources._agentic_table import AgenticTable
from unique_sdk.cli.formatting import (
    format_agentic_table_cell,
    format_agentic_table_cell_history,
    format_agentic_table_sheet,
)
from unique_sdk.cli.state import ShellState

AGENTIC_TABLE_ERROR_PREFIX = "agentic-table:"


def is_error_output(output: str) -> bool:
    """Return ``True`` when *output* is an error message from an ``agentic-table`` command."""
    return output.startswith(AGENTIC_TABLE_ERROR_PREFIX)


def _error(exc: UniqueError) -> str:
    """Render an SDK error as a CLI error line.

    A 403 (the platform's sheet-access guard) is collapsed to a stable
    ``permission denied`` message so agent ``&&`` chains stop cleanly and the
    wording does not leak backend detail; other errors pass through verbatim.
    """
    if exc.http_status == 403:
        return f"{AGENTIC_TABLE_ERROR_PREFIX} permission denied"
    return f"{AGENTIC_TABLE_ERROR_PREFIX} {exc}"


def cmd_get_sheet(
    state: ShellState,
    table_id: str,
    *,
    include_cells: bool = False,
    include_metadata: bool = False,
    output_json: bool = False,
) -> str:
    """Fetch a sheet summary: name, state, row count, and (optionally) metadata/cells."""
    try:
        sheet = asyncio.run(
            AgenticTable.get_sheet_data(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                tableId=table_id,
                includeCells=include_cells,
                includeRowCount=True,
                includeSheetMetadata=include_metadata,
            )
        )
    except UniqueError as exc:
        return _error(exc)

    if output_json:
        return json.dumps(sheet, indent=2, default=str)
    return format_agentic_table_sheet(sheet, include_cells=include_cells)


def cmd_get_cell(
    state: ShellState,
    table_id: str,
    *,
    row_order: int,
    column_order: int,
    output_json: bool = False,
) -> str:
    """Fetch a single cell by row/column order."""
    try:
        cell = asyncio.run(
            AgenticTable.get_cell(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                tableId=table_id,
                rowOrder=row_order,
                columnOrder=column_order,
            )
        )
    except UniqueError as exc:
        return _error(exc)

    if output_json:
        return json.dumps(cell, indent=2, default=str)
    return format_agentic_table_cell(cell)


def cmd_cell_history(
    state: ShellState,
    table_id: str,
    *,
    row_order: int,
    column_order: int,
    output_json: bool = False,
) -> str:
    """Fetch a single cell's log/edit history (``logEntries`` on the cell record)."""
    try:
        cell = asyncio.run(
            AgenticTable.get_cell(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                tableId=table_id,
                rowOrder=row_order,
                columnOrder=column_order,
            )
        )
    except UniqueError as exc:
        return _error(exc)

    if output_json:
        return json.dumps(cell.get("logEntries") or [], indent=2, default=str)
    return format_agentic_table_cell_history(cell)
