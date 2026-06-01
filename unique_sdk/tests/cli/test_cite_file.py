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
    def test_local_file_writes_manifest(self, state: ShellState, workspace: Path):
        result = cmd_cite_file(state, "./report.pdf", "3,5", local=True)

        assert "[filesource1] -> report.pdf page 3" in result
        assert "[filesource2] -> report.pdf page 5" in result

        manifest = workspace / ".unique" / "file-refs.jsonl"
        assert manifest.exists()
        lines = [json.loads(l) for l in manifest.read_text().splitlines()]
        assert len(lines) == 2
        assert lines[0]["sourceNumber"] == 1
        assert lines[0]["contentId"] == "local:./report.pdf"
        assert lines[0]["filename"] == "report.pdf"
        assert lines[0]["page"] == 3
        assert lines[1]["sourceNumber"] == 2
        assert lines[1]["page"] == 5

    def test_whole_file_no_pages(self, state: ShellState, workspace: Path):
        result = cmd_cite_file(state, "./doc.pdf", None, local=True)

        assert "[filesource1] -> doc.pdf page 0" in result

        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(l) for l in manifest.read_text().splitlines()]
        assert len(lines) == 1
        assert lines[0]["page"] == 0

    def test_dedup_same_page(self, state: ShellState, workspace: Path):
        cmd_cite_file(state, "./report.pdf", "3", local=True)
        result = cmd_cite_file(state, "./report.pdf", "3", local=True)

        assert "already declared" in result
        assert "[filesource1]" in result

        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(l) for l in manifest.read_text().splitlines()]
        assert len(lines) == 1

    def test_continues_numbering_across_calls(
        self, state: ShellState, workspace: Path
    ):
        cmd_cite_file(state, "./a.pdf", "1,2", local=True)
        result = cmd_cite_file(state, "./b.pdf", "1", local=True)

        assert "[filesource3] -> b.pdf page 1" in result

    @patch("unique_sdk.cli.commands.cite_file._resolve_content_id")
    def test_kb_file_resolves_content_id(
        self, mock_resolve, state: ShellState, workspace: Path
    ):
        mock_resolve.return_value = ("cont_abc123", "report.pdf")
        result = cmd_cite_file(state, "report.pdf", "3")

        assert "[filesource1] -> report.pdf page 3" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(l) for l in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_abc123"

    def test_invalid_pages_returns_error(self, state: ShellState, workspace: Path):
        result = cmd_cite_file(state, "./report.pdf", "abc", local=True)
        assert CITE_ERROR_PREFIX in result
