"""Tests for the unique-cli agentic-table write commands (full loop)."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from unique_sdk._error import UniqueError
from unique_sdk.api_resources._agentic_table import (
    AgenticTableSheetState,
    MagicTableArtifactState,
    MagicTableArtifactType,
)
from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.agentic_table import is_error_output
from unique_sdk.cli.commands.agentic_table_write import (
    _FAST_POLL_WINDOW_SECONDS,
    _poll_interval,
    cmd_create_sheet,
    cmd_export,
    cmd_import,
    cmd_rerun_row,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState

_CREATED = {
    "sheetId": "mt_new",
    "dueDiligenceId": "dd_1",
    "name": "Vendor DDQ",
    "state": "IDLE",
    "createdBy": "u1",
    "companyId": "c1",
    "createdAt": "2026-01-01T00:00:00.000Z",
}

_OK = {"status": True, "message": "accepted"}


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
        f"unique_sdk.cli.commands.agentic_table_write.AgenticTable.{method}",
        new_callable=AsyncMock,
        **kwargs,
    )


def _no_sleep() -> object:
    return patch(
        "unique_sdk.cli.commands.agentic_table_write.asyncio.sleep",
        new_callable=AsyncMock,
    )


def _artifact(
    artifact_type: str,
    artifact_state: str,
    *,
    content_id: str | None = None,
    updated_at: str = "2026-01-01T00:00:00.000Z",
) -> dict[str, object]:
    return {
        "id": f"art_{artifact_type}_{updated_at}",
        "artifactType": artifact_type,
        "artifactState": artifact_state,
        "contentId": content_id,
        "createdAt": updated_at,
        "updatedAt": updated_at,
    }


# -- create-sheet ----------------------------------------------------------


def test_cmd_create_sheet_human_readable() -> None:
    with _patch("create_sheet", return_value=_CREATED) as mock_create:
        out = cmd_create_sheet(
            _state(), "asst_1", name="Vendor DDQ", due_at="2026-12-31"
        )

    assert "Sheet:" in out and "Vendor DDQ" in out
    assert "ID:" in out and "mt_new" in out
    assert "Due diligence ID:" in out and "dd_1" in out
    kwargs = mock_create.await_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["company_id"] == "c1"
    assert kwargs["assistantId"] == "asst_1"
    assert kwargs["name"] == "Vendor DDQ"
    assert kwargs["dueAt"] == "2026-12-31"


def test_cmd_create_sheet_omits_unset_optionals() -> None:
    with _patch("create_sheet", return_value=_CREATED) as mock_create:
        cmd_create_sheet(_state(), "asst_1")

    kwargs = mock_create.await_args.kwargs
    assert "name" not in kwargs
    assert "dueAt" not in kwargs


def test_cmd_create_sheet_json() -> None:
    with _patch("create_sheet", return_value=_CREATED):
        out = cmd_create_sheet(_state(), "asst_1", output_json=True)

    assert json.loads(out)["sheetId"] == "mt_new"


def test_cmd_create_sheet_maps_403() -> None:
    with _patch("create_sheet", side_effect=UniqueError("Forbidden", http_status=403)):
        out = cmd_create_sheet(_state(), "asst_1")

    assert out == "agentic-table: permission denied"
    assert is_error_output(out)


# -- import (no wait) ------------------------------------------------------


def test_cmd_import_human_readable() -> None:
    with _patch("add_metadata", return_value=_OK) as mock_add:
        out = cmd_import(
            _state(),
            "mt_1",
            question_file_ids=["c_q"],
            source_file_ids=["c_src"],
        )

    assert "Action:" in out and "import" in out
    assert "Result:" in out and "OK" in out
    kwargs = mock_add.await_args.kwargs
    assert kwargs["tableId"] == "mt_1"
    assert kwargs["questionFileIds"] == ["c_q"]
    assert kwargs["sourceFileIds"] == ["c_src"]
    assert "questionTexts" not in kwargs
    assert "context" not in kwargs


def test_cmd_import_json() -> None:
    with _patch("add_metadata", return_value=_OK):
        out = cmd_import(_state(), "mt_1", question_texts=["q?"], output_json=True)

    assert json.loads(out)["result"]["status"] is True


def test_cmd_import_maps_422_verbatim() -> None:
    with _patch(
        "add_metadata",
        side_effect=UniqueError("Sheet is processing", http_status=422),
    ):
        out = cmd_import(_state(), "mt_1", question_texts=["q?"])

    assert out.startswith("agentic-table: ")
    assert "processing" in out.lower()
    assert is_error_output(out)


def test_cmd_import_soft_failure_is_error() -> None:
    """A 200 body with ``status: false`` must fail, not print FAILED and exit 0."""
    with _patch(
        "add_metadata", return_value={"status": False, "message": "sheet is locked"}
    ):
        out = cmd_import(_state(), "mt_1", question_texts=["q?"])

    assert is_error_output(out)
    assert "import rejected" in out
    assert "sheet is locked" in out


def test_cmd_import_soft_failure_skips_wait() -> None:
    """A declined import must not fall through to polling for a run it never triggered."""
    with (
        _patch("add_metadata", return_value={"status": False}),
        _patch("get_sheet_state") as mock_state,
        _no_sleep(),
    ):
        out = cmd_import(_state(), "mt_1", question_texts=["q?"], wait=True)

    assert is_error_output(out)
    assert "no detail returned" in out
    mock_state.assert_not_awaited()


# -- import (--wait) -------------------------------------------------------


def test_cmd_import_wait_run_finishes() -> None:
    states = [
        AgenticTableSheetState.IDLE,  # not started yet
        AgenticTableSheetState.PROCESSING,  # run started
        AgenticTableSheetState.IDLE,  # run finished
    ]
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", side_effect=states),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", question_texts=["q?"], wait=True, timeout=60.0
        )

    assert "Result:" in out and "OK" in out
    assert "Run finished" in out and "IDLE" in out


def test_cmd_import_wait_no_run_started() -> None:
    """Sources alone never trigger a run, so nothing starting is the expected outcome."""
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", return_value=AgenticTableSheetState.IDLE),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", source_file_ids=["c_src"], wait=True, timeout=0.0
        )

    assert "No agent run started" in out
    assert not is_error_output(out)


def test_cmd_import_wait_questions_but_no_run_is_error() -> None:
    """A run was expected but never observed: indeterminate, so break the chain.

    Exiting 0 here would let the documented ``&&`` recipe export a sheet whose
    answers are still being generated.
    """
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", return_value=AgenticTableSheetState.IDLE),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", question_texts=["q?"], wait=True, timeout=0.0
        )

    assert is_error_output(out)
    assert "no run started" in out
    assert "before exporting" in out, "must steer away from exporting an unrun sheet"


def test_cmd_import_wait_timeout_is_error() -> None:
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", return_value=AgenticTableSheetState.PROCESSING),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", question_texts=["q?"], wait=True, timeout=0.0
        )

    assert is_error_output(out)
    assert "timed out" in out


# -- export (no wait) ------------------------------------------------------


def test_cmd_export_human_readable() -> None:
    with _patch("generate_artifact", return_value=_OK) as mock_gen:
        out = cmd_export(_state(), "mt_1", artifact_types=["FULL_REPORT"])

    assert "Action:" in out and "export" in out
    assert "Result:" in out and "OK" in out
    kwargs = mock_gen.await_args.kwargs
    assert kwargs["tableId"] == "mt_1"
    assert kwargs["artifactTypes"] == [MagicTableArtifactType.FULL_REPORT]


def test_cmd_export_json() -> None:
    with _patch("generate_artifact", return_value=_OK):
        out = cmd_export(
            _state(), "mt_1", artifact_types=["FULL_REPORT"], output_json=True
        )

    assert json.loads(out)["result"]["status"] is True


def test_cmd_export_maps_403() -> None:
    with _patch(
        "generate_artifact", side_effect=UniqueError("Forbidden", http_status=403)
    ):
        out = cmd_export(_state(), "mt_1", artifact_types=["FULL_REPORT"])

    assert out == "agentic-table: permission denied"


def test_cmd_export_soft_failure_is_error() -> None:
    with _patch(
        "generate_artifact",
        return_value={"status": False, "message": "nothing to export"},
    ):
        out = cmd_export(_state(), "mt_1", artifact_types=["FULL_REPORT"])

    assert is_error_output(out)
    assert "export rejected" in out
    assert "nothing to export" in out


def test_cmd_export_unknown_type_is_an_error_line_not_an_exception() -> None:
    """``click.Choice`` guards the CLI path; a direct caller has to be told too."""
    with _patch("generate_artifact") as mock_generate:
        out = cmd_export(_state(), "mt_1", artifact_types=["FULL_REPORT", "SUMMARY"])

    assert is_error_output(out)
    assert "unknown artifact type: SUMMARY" in out
    assert "FULL_REPORT" in out  # the valid one is listed as accepted, not rejected
    mock_generate.assert_not_awaited()


def test_cmd_export_soft_failure_skips_wait() -> None:
    """A declined generation must not poll for artifacts that were never queued.

    One call is expected regardless: the freshness baseline is taken before the
    trigger. Anything beyond it would be polling for a generation that a
    ``status: false`` body says never started.
    """
    with (
        _patch("generate_artifact", return_value={"status": False}),
        _patch("list_artifacts", return_value=[]) as mock_list,
        _no_sleep(),
    ):
        out = cmd_export(_state(), "mt_1", artifact_types=["FULL_REPORT"], wait=True)

    assert is_error_output(out)
    assert mock_list.await_count == 1


# -- export (--wait) -------------------------------------------------------


def test_cmd_export_wait_done_lists_artifacts() -> None:
    lists = [
        [],  # pre-trigger snapshot
        [_artifact("FULL_REPORT", MagicTableArtifactState.IN_PROGRESS)],
        [_artifact("FULL_REPORT", MagicTableArtifactState.DONE, content_id="cont_x")],
    ]
    with (
        _patch("generate_artifact", return_value=_OK),
        _patch("list_artifacts", side_effect=lists),
        _no_sleep(),
    ):
        out = cmd_export(
            _state(), "mt_1", artifact_types=["FULL_REPORT"], wait=True, timeout=60.0
        )

    assert "FULL_REPORT" in out and "DONE" in out
    assert "cont_x" in out
    assert not is_error_output(out)


def test_cmd_export_wait_returns_report_finished_between_polls() -> None:
    """The report can go DONE without its IN_PROGRESS phase ever being seen.

    A sheet carries two records per type: the trigger's nameless marker, which
    is never updated to DONE, and the report itself. On a small sheet the report
    is written within one poll interval, so waiting to observe it IN_PROGRESS
    would hang until timeout even though the export succeeded.
    """
    marker = _artifact("FULL_REPORT", MagicTableArtifactState.IN_PROGRESS)
    stale = _artifact(
        "FULL_REPORT", MagicTableArtifactState.DONE, content_id="cont_old"
    )
    fresh = _artifact(
        "FULL_REPORT",
        MagicTableArtifactState.DONE,
        content_id="cont_new",
        updated_at="2026-01-01T00:00:05.000Z",
    )
    lists = [[stale, marker], [stale, marker], [fresh, marker]]
    with (
        _patch("generate_artifact", return_value=_OK),
        _patch("list_artifacts", side_effect=lists),
        _no_sleep(),
    ):
        out = cmd_export(
            _state(), "mt_1", artifact_types=["FULL_REPORT"], wait=True, timeout=60.0
        )

    assert not is_error_output(out)
    assert "cont_new" in out
    assert "cont_old" not in out


def test_cmd_export_wait_error_is_error() -> None:
    lists = [
        [],  # pre-trigger snapshot
        [_artifact("FULL_REPORT", MagicTableArtifactState.IN_PROGRESS)],
        [_artifact("FULL_REPORT", MagicTableArtifactState.ERROR)],
    ]
    with (
        _patch("generate_artifact", return_value=_OK),
        _patch("list_artifacts", side_effect=lists),
        _no_sleep(),
    ):
        out = cmd_export(
            _state(), "mt_1", artifact_types=["FULL_REPORT"], wait=True, timeout=60.0
        )

    assert is_error_output(out)
    assert "failed" in out and "FULL_REPORT" in out


def test_cmd_export_wait_timeout_is_error() -> None:
    with (
        _patch("generate_artifact", return_value=_OK),
        _patch("list_artifacts", return_value=[]),
        _no_sleep(),
    ):
        out = cmd_export(
            _state(), "mt_1", artifact_types=["FULL_REPORT"], wait=True, timeout=0.0
        )

    assert is_error_output(out)
    assert "timed out" in out and "FULL_REPORT" in out


# -- error detector + CLI wiring ------------------------------------------


# -- rerun-row -------------------------------------------------------------


def test_cmd_rerun_row_no_wait() -> None:
    with _patch("rerun_row", return_value=_OK) as mock_rerun:
        out = cmd_rerun_row(_state(), "mt_1", 4)

    assert "Result:" in out and "OK" in out
    assert not is_error_output(out)
    kwargs = mock_rerun.await_args.kwargs
    assert kwargs["tableId"] == "mt_1"
    assert kwargs["rowOrder"] == 4


def test_cmd_rerun_row_soft_failure_is_error() -> None:
    """A locked or final row is declined in a 200 body, so it must still fail."""
    with _patch(
        "rerun_row", return_value={"status": False, "message": "row is locked"}
    ):
        out = cmd_rerun_row(_state(), "mt_1", 4)

    assert is_error_output(out)
    assert "rerun rejected" in out
    assert "row is locked" in out


def test_cmd_rerun_row_soft_failure_skips_wait() -> None:
    with (
        _patch("rerun_row", return_value={"status": False}),
        _patch("get_sheet_state") as mock_state,
        _no_sleep(),
    ):
        out = cmd_rerun_row(_state(), "mt_1", 4, wait=True)

    assert is_error_output(out)
    mock_state.assert_not_awaited()


def test_cmd_rerun_row_permission_denied() -> None:
    with _patch("rerun_row", side_effect=UniqueError("nope", http_status=403)):
        out = cmd_rerun_row(_state(), "mt_1", 4)

    assert out == "agentic-table: permission denied"


def test_cmd_rerun_row_wait_run_finishes() -> None:
    states = [
        AgenticTableSheetState.IDLE,  # not started yet
        AgenticTableSheetState.PROCESSING,  # rerun started
        AgenticTableSheetState.IDLE,  # rerun finished
    ]
    with (
        _patch("rerun_row", return_value=_OK),
        _patch("get_sheet_state", side_effect=states),
        _no_sleep(),
    ):
        out = cmd_rerun_row(_state(), "mt_1", 4, wait=True, timeout=60.0)

    assert "Row 4 rerun finished" in out and "IDLE" in out
    assert not is_error_output(out)


def test_cmd_rerun_row_wait_no_run_is_error() -> None:
    """A rerun always triggers a run, so nothing starting is never benign."""
    with (
        _patch("rerun_row", return_value=_OK),
        _patch("get_sheet_state", return_value=AgenticTableSheetState.IDLE),
        _no_sleep(),
    ):
        out = cmd_rerun_row(_state(), "mt_1", 4, wait=True, timeout=0.0)

    assert is_error_output(out)
    assert "no run started" in out


def test_cmd_rerun_row_wait_timeout_is_error() -> None:
    with (
        _patch("rerun_row", return_value=_OK),
        _patch("get_sheet_state", return_value=AgenticTableSheetState.PROCESSING),
        _no_sleep(),
    ):
        out = cmd_rerun_row(_state(), "mt_1", 4, wait=True, timeout=0.0)

    assert is_error_output(out)
    assert "timed out" in out


def test_error_output_detector() -> None:
    assert is_error_output("agentic-table: permission denied")
    assert not is_error_output("Action:  import")


@patch("unique_sdk.cli.cli.cmd_create_sheet")
def test_cli_create_sheet_wiring(mock_cmd: object) -> None:
    mock_cmd.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "create-sheet", "asst_1", "--name", "DDQ"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 0
    kwargs = mock_cmd.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["name"] == "DDQ"
    assert mock_cmd.call_args.args[1] == "asst_1"  # type: ignore[attr-defined]


@patch("unique_sdk.cli.cli.cmd_import")
def test_cli_import_wiring(mock_cmd: object) -> None:
    mock_cmd.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        [
            "agentic-table",
            "import",
            "mt_1",
            "--question-file-id",
            "c_q",
            "--source-file-id",
            "c_src",
            "--wait",
        ],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 0
    kwargs = mock_cmd.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["question_file_ids"] == ["c_q"]
    assert kwargs["source_file_ids"] == ["c_src"]
    assert kwargs["wait"] is True


@patch("unique_sdk.cli.cli.cmd_export")
def test_cli_export_wiring(mock_cmd: object) -> None:
    mock_cmd.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "export", "mt_1", "--type", "FULL_REPORT", "--json"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 0
    kwargs = mock_cmd.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["artifact_types"] == ["FULL_REPORT"]
    assert kwargs["output_json"] is True


@patch("unique_sdk.cli.cli.cmd_rerun_row")
def test_cli_rerun_row_wiring(mock_cmd: object) -> None:
    mock_cmd.return_value = "ok"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "rerun-row", "mt_1", "4", "--wait"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 0
    assert mock_cmd.call_args.args[1:] == ("mt_1", 4)  # type: ignore[attr-defined]
    assert mock_cmd.call_args.kwargs["wait"] is True  # type: ignore[attr-defined]


@patch("unique_sdk.cli.cli.cmd_rerun_row")
def test_cli_rerun_row_rejects_non_integer_row(mock_cmd: object) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "rerun-row", "mt_1", "abc"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code != 0


@patch("unique_sdk.cli.cli.cmd_export")
def test_cli_export_rejects_invalid_type(mock_cmd: object) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "export", "mt_1", "--type", "NOPE"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code != 0


@pytest.mark.parametrize(
    ("command", "option"),
    [
        ("import", "--timeout"),
        ("import", "--start-timeout"),
        ("export", "--timeout"),
    ],
)
@patch("unique_sdk.cli.cli.cmd_import")
@patch("unique_sdk.cli.cli.cmd_export")
def test_cli_rejects_a_negative_wait_budget(
    mock_export: object, mock_import: object, command: str, option: str
) -> None:
    """A negative budget is a typo, and expires instantly — say so up front."""
    runner = CliRunner()
    extra = ["--type", "FULL_REPORT"] if command == "export" else []

    result = runner.invoke(
        cli_main,
        ["agentic-table", command, "mt_1", *extra, option, "-1", "--wait"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code != 0
    assert option in result.output
    mock_import.assert_not_called()  # type: ignore[attr-defined]
    mock_export.assert_not_called()  # type: ignore[attr-defined]


@patch("unique_sdk.cli.cli.cmd_import")
def test_cli_write_error_exits_non_zero(mock_cmd: object) -> None:
    mock_cmd.return_value = "agentic-table: permission denied"  # type: ignore[attr-defined]
    runner = CliRunner()

    result = runner.invoke(
        cli_main,
        ["agentic-table", "import", "mt_1", "--question-text", "q?"],
        env={"UNIQUE_USER_ID": "u1", "UNIQUE_COMPANY_ID": "c1"},
    )

    assert result.exit_code == 1
    assert result.output.strip() == "agentic-table: permission denied"


# -- polling behaviour -----------------------------------------------------


def test_poll_interval_is_dense_before_settling() -> None:
    """A short run fits inside one settled interval, so the opening window is
    sampled closely; otherwise a run that finished looks like one that never
    started."""
    now = time.monotonic()
    assert _poll_interval(now, 5.0) == 1.0
    assert _poll_interval(now - _FAST_POLL_WINDOW_SECONDS - 1, 5.0) == 5.0


def test_poll_interval_never_exceeds_the_callers_interval() -> None:
    assert _poll_interval(time.monotonic(), 0.25) == 0.25


def test_wait_survives_a_transient_read_failure() -> None:
    """The write already landed, so one failed poll must not report it as failed."""
    states = [
        UniqueError("bad gateway", http_status=502),
        AgenticTableSheetState.PROCESSING,
        AgenticTableSheetState.IDLE,
    ]
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", side_effect=states),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", question_texts=["q?"], wait=True, timeout=60.0
        )

    assert not is_error_output(out)
    assert "Run finished" in out


def test_wait_does_not_retry_a_denial() -> None:
    """A 403 is a decision rather than a blip: retrying only delays the report."""
    with (
        _patch(
            "get_sheet_state", side_effect=UniqueError("nope", http_status=403)
        ) as mock_state,
        _patch("add_metadata", return_value=_OK),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", question_texts=["q?"], wait=True, timeout=60.0
        )

    assert out == "agentic-table: permission denied"
    assert mock_state.await_count == 1


def test_wait_gives_up_after_repeated_read_failures() -> None:
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", side_effect=UniqueError("down", http_status=502)),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(), "mt_1", question_texts=["q?"], wait=True, timeout=60.0
        )

    assert is_error_output(out)


def test_export_wait_accepts_a_new_artifact_with_no_timestamp() -> None:
    """Freshness falls back to identity when ``updatedAt`` is absent.

    Comparing two missing timestamps would exclude the artifact on every poll
    and hang the wait on a generation that had in fact succeeded.
    """
    stale = _artifact("FULL_REPORT", "IN_PROGRESS")
    fresh = {
        "id": "art_new",
        "artifactType": "FULL_REPORT",
        "artifactState": "DONE",
        "contentId": "cont_1",
    }
    with (
        _patch("generate_artifact", return_value=_OK),
        _patch("list_artifacts", side_effect=[[stale], [stale, fresh]]),
        _no_sleep(),
    ):
        out = cmd_export(
            _state(),
            "mt_1",
            artifact_types=[MagicTableArtifactType.FULL_REPORT],
            wait=True,
            timeout=60.0,
        )

    assert not is_error_output(out)
    assert "cont_1" in out


# -- --json shapes under --wait --------------------------------------------


def test_cmd_import_wait_json_shape() -> None:
    """Agents pipe this to jq, so the keys --wait adds are part of the contract."""
    states = [
        AgenticTableSheetState.IDLE,
        AgenticTableSheetState.PROCESSING,
        AgenticTableSheetState.IDLE,
    ]
    with (
        _patch("add_metadata", return_value=_OK),
        _patch("get_sheet_state", side_effect=states),
        _no_sleep(),
    ):
        out = cmd_import(
            _state(),
            "mt_1",
            question_texts=["q?"],
            wait=True,
            timeout=60.0,
            output_json=True,
        )

    payload = json.loads(out)
    assert payload["result"] == _OK
    assert payload["runStarted"] is True
    assert payload["finalState"] == "IDLE"


def test_cmd_export_wait_json_shape() -> None:
    stale = _artifact("FULL_REPORT", "DONE", updated_at="2026-01-01T00:00:00.000Z")
    fresh = _artifact(
        "FULL_REPORT",
        "DONE",
        content_id="cont_1",
        updated_at="2026-01-02T00:00:00.000Z",
    )
    with (
        _patch("generate_artifact", return_value=_OK),
        _patch("list_artifacts", side_effect=[[stale], [stale, fresh]]),
        _no_sleep(),
    ):
        out = cmd_export(
            _state(),
            "mt_1",
            artifact_types=[MagicTableArtifactType.FULL_REPORT],
            wait=True,
            timeout=60.0,
            output_json=True,
        )

    payload = json.loads(out)
    assert payload["result"] == _OK
    assert [a["contentId"] for a in payload["artifacts"]] == ["cont_1"]


def test_missing_status_field_is_not_reported_as_a_rejection() -> None:
    """An unintelligible body may mean the mutation landed; do not invite a retry."""
    with _patch("add_metadata", return_value={}):
        out = cmd_import(_state(), "mt_1", question_texts=["q?"])

    assert is_error_output(out)
    assert "outcome is unknown" in out
    assert "rejected" not in out
