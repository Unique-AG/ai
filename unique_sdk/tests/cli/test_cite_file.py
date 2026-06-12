"""Tests for unique-cli cite command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from unique_sdk.cli.commands.cite_file import (
    CITE_ERROR_PREFIX,
    _parse_pages,
    cmd_cite_file,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState


@pytest.fixture
def state() -> ShellState:
    config = Config(
        user_id="user_test",
        company_id="comp_test",
        api_key="key",
        app_id="app",
        api_base="http://localhost",
    )
    return ShellState(config=config)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def workspace_with_manifest(workspace: Path) -> Path:
    """Workspace with a chat-files.json manifest mapping filenames to content IDs."""
    unique_dir = workspace / ".unique"
    unique_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"report.pdf": "cont_chat123", "data.xlsx": "cont_chat456"}
    (unique_dir / "chat-files.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return workspace


class TestParsePages:
    def test_none_returns_whole_file(self):
        assert _parse_pages(None) == [0]

    def test_empty_returns_whole_file(self):
        assert _parse_pages("") == [0]

    def test_single_page(self):
        assert _parse_pages("3") == [3]

    def test_comma_separated(self):
        assert _parse_pages("1,3,5") == [1, 3, 5]

    def test_range(self):
        assert _parse_pages("3-7") == [3, 4, 5, 6, 7]

    def test_mixed(self):
        assert _parse_pages("1,3-5,9") == [1, 3, 4, 5, 9]

    def test_deduplicates(self):
        assert _parse_pages("3,3,5") == [3, 5]

    def test_invalid_returns_empty(self):
        assert _parse_pages("abc") == []

    def test_invalid_range_returns_empty(self):
        assert _parse_pages("5-3") == []

    def test_comma_only_returns_empty(self):
        assert _parse_pages(",") == []
        assert _parse_pages(",,") == []

    def test_huge_range_returns_empty(self):
        assert _parse_pages("1-1000000") == []

    def test_max_boundary_accepted(self):
        result = _parse_pages("1-500")
        assert len(result) == 500


class TestCmdCiteFile:
    def test_manifest_resolves_chat_file(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "3,5")

        assert "[filesource1] -> report.pdf page 3" in result
        assert "[filesource2] -> report.pdf page 5" in result

        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        assert manifest.exists()
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert len(lines) == 2
        assert lines[0]["contentId"] == "cont_chat123"
        assert lines[0]["filename"] == "report.pdf"
        assert lines[0]["page"] == 3
        assert lines[1]["contentId"] == "cont_chat123"
        assert lines[1]["page"] == 5

    def test_manifest_basename_lookup(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        """Passing a path resolves via basename against the manifest."""
        result = cmd_cite_file(state, "./downloads/report.pdf", "1")

        assert "[filesource1] -> report.pdf page 1" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_chat123"

    @patch("unique_sdk.cli.commands.cite_file._resolve_content_id")
    def test_fallback_to_kb_when_not_in_manifest(
        self, mock_resolve, state: ShellState, workspace_with_manifest: Path
    ):
        """File not in manifest falls through to KB resolution."""
        mock_resolve.return_value = ("cont_kb789", "unknown.pdf")
        result = cmd_cite_file(state, "unknown.pdf", "2")

        assert "[filesource1] -> unknown.pdf page 2" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_kb789"

    @patch("unique_sdk.cli.commands.cite_file._resolve_content_id")
    def test_kb_file_resolves_content_id(
        self, mock_resolve, state: ShellState, workspace: Path
    ):
        """Without manifest, resolves via KB API."""
        mock_resolve.return_value = ("cont_abc123", "report.pdf")
        result = cmd_cite_file(state, "report.pdf", "3")

        assert "[filesource1] -> report.pdf page 3" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_abc123"

    def test_content_id_passthrough(self, state: ShellState, workspace: Path):
        """Content IDs starting with cont_ are used directly."""
        result = cmd_cite_file(state, "cont_direct999", "1")

        assert "[filesource1] -> cont_direct999 page 1" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_direct999"

    def test_whole_file_no_pages(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", None)

        assert "[filesource1] -> report.pdf page 0" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["page"] == 0

    def test_dedup_same_page(self, state: ShellState, workspace_with_manifest: Path):
        cmd_cite_file(state, "report.pdf", "3")
        result = cmd_cite_file(state, "report.pdf", "3")

        assert "already declared" in result
        assert "[filesource1]" in result

        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert len(lines) == 1

    def test_continues_numbering_across_calls(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        cmd_cite_file(state, "report.pdf", "1,2")
        result = cmd_cite_file(state, "data.xlsx", "1")

        assert "[filesource3] -> data.xlsx page 1" in result

    def test_invalid_pages_returns_error(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "abc")
        assert CITE_ERROR_PREFIX in result

    def test_metadata_filter_blocks_out_of_scope_cont_id(
        self, state: ShellState, workspace: Path
    ):
        """A per-message filter blocks citing a KB doc outside the scope."""
        state.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_allowed"],
        }
        state._chat_file_content_ids_cache = set()
        result = cmd_cite_file(state, "cont_blocked", "1")
        assert CITE_ERROR_PREFIX in result
        assert "task scope" in result
        # Nothing should be written when denied.
        assert not (workspace / ".unique" / "file-refs.jsonl").exists()

    def test_metadata_filter_allows_chat_attached_file(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        """Chat-attached files stay citeable even when the filter excludes them."""
        state.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_other"],
        }
        result = cmd_cite_file(state, "report.pdf", "1")
        assert CITE_ERROR_PREFIX not in result
        assert "[filesource1] -> report.pdf page 1" in result
