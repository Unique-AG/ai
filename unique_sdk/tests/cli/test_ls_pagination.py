"""Tests for ``ls`` paging: --skip, --limit, --all and the truncation note (UN-27614)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from unique_sdk.cli.cli import main
from unique_sdk.cli.commands.navigation import (
    LS_DEFAULT_LIMIT,
    LS_MAX_LIMIT,
    cmd_ls,
    is_ls_error_output,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.shell import UniqueShell
from unique_sdk.cli.state import ShellState


def _state() -> ShellState:
    """A shell inside /Reports: the root lists no files of its own."""
    state = ShellState(
        Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
    )
    state._path = "/Reports"
    state._scope_id = "scope_r"
    return state


def _fake_infos(
    rows_key: str, rows: list[dict[str, Any]], calls: list[dict[str, Any]]
) -> Callable[..., dict[str, Any]]:
    """A paged endpoint: honours skip/take and rejects take > 100 like the server."""

    def get_infos(**params: Any) -> dict[str, Any]:
        skip = params.get("skip", 0)
        take = params.get("take", 50)
        assert 1 <= take <= 100
        calls.append({"skip": skip, "take": take})
        return {rows_key: rows[skip : skip + take], "totalCount": len(rows)}

    return get_infos


def _files(n: int) -> list[dict[str, Any]]:
    return [
        {
            "id": f"cont_{i:04d}",
            "key": f"file-{i:04d}.txt",
            "title": f"file-{i:04d}.txt",
            "mimeType": "text/plain",
            "byteSize": 10,
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }
        for i in range(1, n + 1)
    ]


def _folders(n: int) -> list[dict[str, Any]]:
    return [
        {
            "id": f"scope_{i:04d}",
            "name": f"dir-{i:04d}",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-01-01T00:00:00Z",
        }
        for i in range(1, n + 1)
    ]


class _Backend:
    def __init__(self, files: int, folders: int = 0) -> None:
        self.file_calls: list[dict[str, Any]] = []
        self.folder_calls: list[dict[str, Any]] = []
        self._patches = [
            patch(
                "unique_sdk.Content.get_infos",
                side_effect=_fake_infos("contentInfos", _files(files), self.file_calls),
            ),
            patch(
                "unique_sdk.Folder.get_folder_path",
                return_value={"folderPath": "/Reports"},
            ),
            patch(
                "unique_sdk.Folder.get_infos",
                side_effect=_fake_infos(
                    "folderInfos", _folders(folders), self.folder_calls
                ),
            ),
        ]

    def __enter__(self) -> _Backend:
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *_: object) -> None:
        for p in self._patches:
            p.stop()


def _rows(output: str, kind: str) -> list[str]:
    return [line for line in output.splitlines() if line.startswith(kind)]


@pytest.mark.ai
def test_cmd_ls_default_shows_50_and_says_the_rest_is_hidden() -> None:
    """Purpose: A truncated listing is never silent.
    Why this matters: A silent 50-row cap made agents loop (UN-27614).
    Setup summary: 120 files at the root; default limit.
    """
    with _Backend(files=120):
        out = cmd_ls(_state())
    assert len(_rows(out, "FILE")) == LS_DEFAULT_LIMIT
    assert "0 folder(s), 120 file(s)" in out
    assert "showing files 1-50 of 120" in out
    assert "--skip 50" in out
    assert "--all" in out


@pytest.mark.ai
def test_cmd_ls_complete_listing_keeps_the_old_output() -> None:
    """Purpose: A listing that fits has no note.
    Why this matters: Existing callers parse the summary line.
    Setup summary: 3 files, 2 folders.
    """
    with _Backend(files=3, folders=2):
        out = cmd_ls(_state())
    assert out.endswith("2 folder(s), 3 file(s)")
    assert "showing" not in out


@pytest.mark.ai
def test_cmd_ls_skip_pages_to_the_next_rows() -> None:
    """Purpose: --skip reaches rows past the first page.
    Why this matters: Needles at position 51+ must be reachable.
    Setup summary: 120 files; skip 50.
    """
    with _Backend(files=120):
        out = cmd_ls(_state(), skip=50)
    names = [line.split()[1] for line in _rows(out, "FILE")]
    assert names[0] == "file-0051.txt"
    assert names[-1] == "file-0100.txt"
    assert "showing files 51-100 of 120" in out
    assert "--skip 100" in out


@pytest.mark.ai
def test_cmd_ls_last_page_has_range_but_no_more_hint() -> None:
    """Purpose: The last page says where it ends and stops pointing forward.
    Why this matters: The agent must know the listing is complete.
    Setup summary: 120 files; skip 100.
    """
    with _Backend(files=120):
        out = cmd_ls(_state(), skip=100)
    assert len(_rows(out, "FILE")) == 20
    assert "showing files 101-120 of 120" in out
    assert "more:" not in out


@pytest.mark.ai
def test_cmd_ls_all_pages_in_batches_of_100() -> None:
    """Purpose: --all lists every row with server-legal page sizes.
    Why this matters: The server rejects take > 100.
    Setup summary: 230 files; --all.
    """
    with _Backend(files=230) as backend:
        out = cmd_ls(_state(), all_items=True)
    assert len(_rows(out, "FILE")) == 230
    assert "showing" not in out
    assert [c["take"] for c in backend.file_calls] == [100, 100, 100]
    assert [c["skip"] for c in backend.file_calls] == [0, 100, 200]


@pytest.mark.ai
def test_cmd_ls_all_stops_at_the_safety_cap() -> None:
    """Purpose: --all is bounded.
    Why this matters: One call must not page a whole knowledge base.
    Setup summary: more files than the cap.
    """
    with _Backend(files=LS_MAX_LIMIT + 150) as backend:
        out = cmd_ls(_state(), all_items=True)
    assert len(_rows(out, "FILE")) == LS_MAX_LIMIT
    assert len(backend.file_calls) == LS_MAX_LIMIT // 100
    assert f"--skip {LS_MAX_LIMIT}" in out
    # --all restarts at row 0, so at the cap it would only repeat these rows.
    assert "--all" not in out


@pytest.mark.ai
def test_cmd_ls_later_page_does_not_offer_all() -> None:
    """Purpose: --all is only suggested when it reaches rows this call did not.
    Why this matters: --all restarts at row 0; offering it mid-listing loops (Bugbot).
    Setup summary: 230 files; skip 50.
    """
    with _Backend(files=230):
        out = cmd_ls(_state(), skip=50)
    assert "--skip 100" in out
    assert "--all" not in out


@pytest.mark.ai
def test_cmd_ls_limit_and_skip_apply_to_folders_and_files() -> None:
    """Purpose: Both row types page together.
    Why this matters: A folder with many sub-folders is capped like a file list.
    Setup summary: 70 folders, 70 files, limit 60.
    """
    with _Backend(files=70, folders=70):
        out = cmd_ls(_state(), limit=60)
    assert len(_rows(out, "DIR")) == 60
    assert len(_rows(out, "FILE")) == 60
    assert "folders 1-60 of 70" in out
    assert "files 1-60 of 70" in out
    assert "--limit 60" in out


@pytest.mark.ai
@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"skip": -1}, "--skip"),
        ({"limit": 0}, "--limit"),
        ({"limit": LS_MAX_LIMIT + 1}, "--limit"),
    ],
)
def test_cmd_ls_rejects_bad_numbers(kwargs: dict[str, int], message: str) -> None:
    """Purpose: Bad numbers fail before any API call.
    Why this matters: The one-shot CLI must exit non-zero.
    Setup summary: Negative skip, zero limit, limit above the cap.
    """
    with _Backend(files=1) as backend:
        out = cmd_ls(_state(), **kwargs)
    assert out.startswith("ls:")
    assert message in out
    assert is_ls_error_output(out) is True
    assert backend.file_calls == []


@pytest.mark.ai
@pytest.mark.parametrize("kwargs", [{"all_items": True}, {"skip": 5, "limit": 5}])
def test_cmd_ls_root_paging_never_reads_company_wide_files(
    kwargs: dict[str, Any],
) -> None:
    """Purpose: Paging at the root pages root folders only and never reads content.
    Why this matters: A company-wide file read there let an agent page the whole
    knowledge base as if it were top level (UN-24304).
    Setup summary: Root with 12 folders and a content backend that must stay unused.
    """
    state = _state()
    state._path = "/"
    state._scope_id = None
    with _Backend(files=500, folders=12) as backend:
        out = cmd_ls(state, **kwargs)
    assert backend.file_calls == []
    assert _rows(out, "FILE") == []
    assert "0 file(s)" in out
    assert len(backend.folder_calls) >= 1


@pytest.mark.ai
def test_cmd_ls_all_with_limit_is_rejected() -> None:
    """Purpose: --all together with --limit is an error, not a silent --all.
    Why this matters: The caller asked for a window the CLI would not honour.
    Setup summary: 120 files; --all with limit 20.
    """
    with _Backend(files=120) as backend:
        out = cmd_ls(_state(), limit=20, all_items=True)
    assert out == "ls: --all and --limit cannot be combined"
    assert is_ls_error_output(out) is True
    assert backend.file_calls == []


@pytest.mark.ai
def test_cmd_ls_skip_at_scoped_root_is_rejected() -> None:
    """Purpose: --skip at a task-scoped root says paging is unsupported.
    Why this matters: The root list is fixed; ignoring --skip hid that.
    Setup summary: Root with a workspace scope id; skip 50.
    """
    state = _state()
    state._path = "/"
    state._scope_id = None
    state.workspace_scope_ids = ["scope_a"]
    out = cmd_ls(state, skip=50)
    assert out == "ls: paging is not supported at the scoped root"
    assert is_ls_error_output(out) is True


@pytest.mark.ai
def test_cmd_ls_task_scope_note_says_rows_were_hidden() -> None:
    """Purpose: The paging note does not claim rows the task scope hid.
    Why this matters: "showing files 1-50" next to a shorter table misled agents.
    Setup summary: 120 files, task scope keeps the even-numbered ones.
    """
    state = _state()
    state.workspace_metadata_filter = {"and": []}
    with (
        _Backend(files=120),
        patch.object(
            ShellState, "folder_allowed_by_metadata_filter", return_value=True
        ),
        patch.object(
            ShellState,
            "is_content_within_workspace",
            side_effect=lambda cid: int(cid[-4:]) % 2 == 0,
        ),
    ):
        out = cmd_ls(state)
    assert len(_rows(out, "FILE")) == 25
    assert "read files 1-50 of 120 (25 file(s) hidden by task scope)" in out
    assert "showing" not in out
    assert "--skip 50" in out


@pytest.mark.ai
def test_cli_ls_flags_reach_cmd_ls() -> None:
    """Purpose: The Click command forwards --skip, --limit and --all.
    Why this matters: The agent calls the one-shot CLI.
    Setup summary: cmd_ls is mocked; three invocations.
    """
    runner = CliRunner()
    with (
        patch("unique_sdk.cli.cli.cmd_ls", return_value="ok") as mock_ls,
        patch("unique_sdk.cli.cli.LazyState.get", return_value=_state()),
    ):
        assert runner.invoke(main, ["ls", "/A", "--skip", "50"]).exit_code == 0
        assert runner.invoke(main, ["ls", "/A", "-l", "20"]).exit_code == 0
        assert runner.invoke(main, ["ls", "/A", "--all"]).exit_code == 0
    kwargs = [c.kwargs for c in mock_ls.call_args_list]
    assert kwargs[0] == {"skip": 50, "limit": LS_DEFAULT_LIMIT, "all_items": False}
    assert kwargs[1] == {"skip": 0, "limit": 20, "all_items": False}
    assert kwargs[2] == {"skip": 0, "limit": LS_DEFAULT_LIMIT, "all_items": True}


@pytest.mark.ai
def test_cli_ls_bad_limit_exits_non_zero() -> None:
    """Purpose: A bad --limit is an error exit, not a listing.
    Why this matters: Agents read the exit code.
    Setup summary: --limit 0 through the Click command.
    """
    with patch("unique_sdk.cli.cli.LazyState.get", return_value=_state()):
        result = CliRunner().invoke(main, ["ls", "--limit", "0"])
    assert result.exit_code != 0


@pytest.mark.ai
@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        ("", {"target": None, "skip": 0, "limit": LS_DEFAULT_LIMIT, "all": False}),
        ("/A --skip 50", {"target": "/A", "skip": 50, "limit": 50, "all": False}),
        ("-l 20 /A", {"target": "/A", "skip": 0, "limit": 20, "all": False}),
        ("--all", {"target": None, "skip": 0, "limit": 50, "all": True}),
        ("/A --limit=20", {"target": "/A", "skip": 0, "limit": 20, "all": False}),
        ("--skip=50 /A", {"target": "/A", "skip": 50, "limit": 50, "all": False}),
    ],
)
def test_shell_do_ls_parses_flags(arg: str, expected: dict[str, Any]) -> None:
    """Purpose: The REPL ls accepts the same flags as the CLI.
    Why this matters: Shell and one-shot mode must not differ.
    Setup summary: cmd_ls is mocked; arguments vary.
    """
    shell = UniqueShell(_state())
    with patch("unique_sdk.cli.shell.cmd_ls", return_value="ok") as mock_ls:
        shell.do_ls(arg)
    call: MagicMock = mock_ls.call_args
    assert call.args[1] == expected["target"]
    assert call.kwargs == {
        "skip": expected["skip"],
        "limit": expected["limit"],
        "all_items": expected["all"],
    }


@pytest.mark.ai
@pytest.mark.parametrize("arg", ["--limit", "--limit x", "--bogus", "/A /B"])
def test_shell_do_ls_rejects_bad_arguments(arg: str) -> None:
    """Purpose: Bad REPL arguments print an ls error and call nothing.
    Why this matters: A typo must not list the wrong folder.
    Setup summary: Missing value, non-number, unknown flag, two targets.
    """
    shell = UniqueShell(_state())
    with (
        patch("unique_sdk.cli.shell.cmd_ls") as mock_ls,
        patch.object(shell, "_print") as mock_print,
    ):
        shell.do_ls(arg)
    mock_ls.assert_not_called()
    assert mock_print.call_args.args[0].startswith("ls:")
