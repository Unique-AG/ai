"""Tests for the unique-cli agentic-table read commands."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from unique_sdk._error import UniqueError
from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.agentic_table import (
    cmd_cell_history,
    cmd_get_cell,
    cmd_get_sheet,
    is_error_output,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState

_SHEET = {
    "sheetId": "mt_1",
    "name": "Due Diligence Q1",
    "state": "IDLE",
    "createdBy": "u1",
    "companyId": "c1",
    "createdAt": "2026-01-01T00:00:00.000Z",
    "magicTableRowCount": 3,
    "magicTableSheetMetadata": [{"key": "region", "value": "EU"}],
    "magicTableCells": [
        {"rowOrder": 0, "columnOrder": 0, "text": "Question"},
        {"rowOrder": 1, "columnOrder": 0, "text": "What is the fee?"},
    ],
}

_CELL = {
    "sheetId": "mt_1",
    "rowOrder": 1,
    "columnOrder": 2,
    "text": "The management fee is 2%.",
    "rowLocked": False,
    "logEntries": [
        {
            "text": "Answered from source [source1]",
            "createdAt": "2026-01-02T09:30:00.000Z",
            "actorType": "ASSISTANT",
            "messageId": "msg_9",
        }
    ],
}


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state() -> ShellState:
    return ShellState(_config())


def _patch(method: str, **kwargs: object) -> object:
    return patch(
        f"unique_sdk.cli.commands.agentic_table.AgenticTable.{method}",
        new_callable=AsyncMock,
        **kwargs,
    )


# -- get-sheet -------------------------------------------------------------


def test_cmd_get_sheet_human_readable() -> None:
    with _patch("get_sheet_data", return_value=_SHEET) as mock_get:
        out = cmd_get_sheet(_state(), "mt_1", include_cells=True, include_metadata=True)

    assert "Sheet:" in out and "Due Diligence Q1" in out
    assert "State:" in out and "IDLE" in out
    assert "Rows:" in out and "3" in out
    assert "region:" in out and "EU" in out
    assert "What is the fee?" in out
    kwargs = mock_get.await_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["company_id"] == "c1"
    assert kwargs["tableId"] == "mt_1"
    assert kwargs["includeCells"] is True
    assert kwargs["includeSheetMetadata"] is True
    assert kwargs["includeRowCount"] is True


def test_cmd_get_sheet_json() -> None:
    with _patch("get_sheet_data", return_value=_SHEET):
        out = cmd_get_sheet(_state(), "mt_1", output_json=True)

    assert json.loads(out)["sheetId"] == "mt_1"


def test_cmd_get_sheet_maps_403_to_permission_denied() -> None:
    with _patch(
        "get_sheet_data", side_effect=UniqueError("Forbidden", http_status=403)
    ):
        out = cmd_get_sheet(_state(), "mt_1")

    assert out == "agentic-table: permission denied"
    assert is_error_output(out)


def test_cmd_get_sheet_surfaces_other_errors() -> None:
    with _patch("get_sheet_data", side_effect=UniqueError("boom", http_status=500)):
        out = cmd_get_sheet(_state(), "mt_1")

    assert out.startswith("agentic-table: ")
    assert "boom" in out
    assert is_error_output(out)


# -- get-cell --------------------------------------------------------------


def test_cmd_get_cell_human_readable() -> None:
    with _patch("get_cell", return_value=_CELL) as mock_get:
        out = cmd_get_cell(_state(), "mt_1", row_order=1, column_order=2)

    assert "Row:" in out and "Column:" in out
    assert "Locked:" in out and "no" in out
    assert "The management fee is 2%." in out
    kwargs = mock_get.await_args.kwargs
    assert kwargs["tableId"] == "mt_1"
    assert kwargs["rowOrder"] == 1
    assert kwargs["columnOrder"] == 2


def test_cmd_get_cell_json() -> None:
    with _patch("get_cell", return_value=_CELL):
        out = cmd_get_cell(
            _state(), "mt_1", row_order=1, column_order=2, output_json=True
        )

    assert json.loads(out)["text"] == "The management fee is 2%."


# -- cell-history ----------------------------------------------------------


def test_cmd_cell_history_human_readable() -> None:
    with _patch("get_cell", return_value=_CELL):
        out = cmd_cell_history(_state(), "mt_1", row_order=1, column_order=2)

    assert "Cell history (row 1, col 2)" in out
    assert "ASSISTANT" in out
    assert "[msg_9]" in out
    assert "Answered from source [source1]" in out


def test_cmd_cell_history_json_returns_entries_only() -> None:
    with _patch("get_cell", return_value=_CELL):
        out = cmd_cell_history(
            _state(), "mt_1", row_order=1, column_order=2, output_json=True
        )

    entries = json.loads(out)
    assert isinstance(entries, list)
    assert entries[0]["messageId"] == "msg_9"


def test_cmd_cell_history_handles_no_entries() -> None:
    cell = {**_CELL, "logEntries": []}
    with _patch("get_cell", return_value=cell):
        out = cmd_cell_history(_state(), "mt_1", row_order=1, column_order=2)

    assert "(no log entries)" in out


# -- error detector + CLI wiring ------------------------------------------


def test_error_output_detector() -> None:
    assert is_error_output("agentic-table: permission denied")
    assert not is_error_output("Sheet: Due Diligence Q1")


@patch("unique_sdk.cli.cli.cmd_get_sheet")
def test_cli_get_sheet_wiring(mock_cmd: object) -> None:
    mock_cmd.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "get-sheet", "mt_1", "--cells", "--metadata"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 0
    assert result.output.strip() == "ok"
    kwargs = mock_cmd.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["include_cells"] is True
    assert kwargs["include_metadata"] is True
    assert mock_cmd.call_args.args[1] == "mt_1"  # type: ignore[attr-defined]


@patch("unique_sdk.cli.cli.cmd_get_cell")
def test_cli_get_cell_wiring(mock_cmd: object) -> None:
    mock_cmd.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "get-cell", "mt_1", "--row", "1", "--col", "2"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 0
    kwargs = mock_cmd.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["row_order"] == 1
    assert kwargs["column_order"] == 2


@patch("unique_sdk.cli.cli.cmd_get_sheet")
def test_cli_error_exits_non_zero(mock_cmd: object) -> None:
    mock_cmd.return_value = "agentic-table: permission denied"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "get-sheet", "mt_1"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 1
    assert result.output.strip() == "agentic-table: permission denied"
