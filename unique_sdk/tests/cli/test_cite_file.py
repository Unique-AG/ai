"""Tests for unique-cli cite command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unique_sdk.cli.commands.cite_file import (
    CITE_ERROR_PREFIX,
    READ_METHODS,
    _is_non_paginated,
    _normalize_read_method,
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
        result = cmd_cite_file(state, "report.pdf", "3,5", "text")

        assert "[filesource1] -> report.pdf page 3" in result
        assert "[filesource2] -> report.pdf page 5" in result

        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        assert manifest.exists()
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert len(lines) == 2
        assert lines[0]["contentId"] == "cont_chat123"
        assert lines[0]["filename"] == "report.pdf"
        assert lines[0]["page"] == 3
        assert lines[0]["readMethod"] == "text"
        assert lines[1]["contentId"] == "cont_chat123"
        assert lines[1]["page"] == 5
        assert lines[1]["readMethod"] == "text"

    def test_manifest_basename_lookup(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        """Passing a path resolves via basename against the manifest."""
        result = cmd_cite_file(state, "./downloads/report.pdf", "1", "text")

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
        result = cmd_cite_file(state, "unknown.pdf", "2", "text")

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
        result = cmd_cite_file(state, "report.pdf", "3", "text")

        assert "[filesource1] -> report.pdf page 3" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_abc123"

    @patch("unique_sdk.Content.get_info")
    def test_content_id_resolves_title(
        self, mock_info, state: ShellState, workspace: Path
    ):
        """A bare cont_ id is cited with its resolved document title.

        Citing directly by id (the recommended path after `read`) must still
        render the filename, not the opaque id — the manifest stores the
        resolved title. See UN-21780.
        """
        mock_info.return_value = {
            "contentInfo": [{"id": "cont_direct999", "title": "Q3 Report.pdf"}]
        }
        result = cmd_cite_file(state, "cont_direct999", "1", "text")

        assert "[filesource1] -> Q3 Report.pdf page 1" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_direct999"
        assert lines[0]["filename"] == "Q3 Report.pdf"

    @patch("unique_sdk.Content.get_info")
    def test_content_id_falls_back_to_id_when_title_unresolved(
        self, mock_info, state: ShellState, workspace: Path
    ):
        """If the title can't be resolved, the id is used as the filename."""
        mock_info.side_effect = Exception("boom")
        result = cmd_cite_file(state, "cont_direct999", "1", "text")

        assert "[filesource1] -> cont_direct999 page 1" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_direct999"
        assert lines[0]["filename"] == "cont_direct999"

    def test_content_id_passthrough(self, state: ShellState, workspace: Path):
        """Content IDs starting with cont_ are used directly."""
        result = cmd_cite_file(state, "cont_direct999", "1", "indexed")

        assert "[filesource1] -> cont_direct999 page 1" in result
        manifest = workspace / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["contentId"] == "cont_direct999"
        assert lines[0]["readMethod"] == "indexed"

    def test_whole_file_no_pages(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", None, "text")

        assert "[filesource1] -> report.pdf page 0" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["page"] == 0

    def test_dedup_same_page(self, state: ShellState, workspace_with_manifest: Path):
        cmd_cite_file(state, "report.pdf", "3", "text")
        result = cmd_cite_file(state, "report.pdf", "3", "text")

        assert "already declared" in result
        assert "[filesource1]" in result

        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert len(lines) == 1

    def test_recite_same_page_different_method_keeps_first_and_flags(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        # Bugbot #2: re-citing a page with a different --read-method must not
        # silently keep the old method; it surfaces the conflict and keeps first.
        cmd_cite_file(state, "report.pdf", "3", "text")
        result = cmd_cite_file(state, "report.pdf", "3", "vision")

        assert "already declared with --read-method text" in result
        assert "[filesource1]" in result

        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        page3 = [entry for entry in lines if entry["page"] == 3]
        assert len(page3) == 1
        assert page3[0]["readMethod"] == "text"

    def test_continues_numbering_across_calls(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        cmd_cite_file(state, "report.pdf", "1,2", "text")
        result = cmd_cite_file(state, "data.xlsx", None, "indexed")

        assert "[filesource3] -> data.xlsx page 0" in result

    def test_invalid_pages_returns_error(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "abc", "text")
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
        result = cmd_cite_file(state, "cont_blocked", "1", "text")
        assert CITE_ERROR_PREFIX in result
        assert "task scope" in result
        # Nothing should be written when denied.
        assert not (workspace / ".unique" / "file-refs.jsonl").exists()

    @patch("unique_sdk.Content.get_info")
    def test_out_of_scope_cont_id_denied_before_title_fetch(
        self, mock_get_info: MagicMock, state: ShellState, workspace: Path
    ):
        """Citing an out-of-scope cont_ id must deny *before* resolving its
        title, so no Content.get_info probes the KB (the cross-scope existence/
        title oracle). See UN-21780.
        """
        state.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_allowed"],
        }
        state._chat_file_content_ids_cache = set()
        result = cmd_cite_file(state, "cont_blocked", "1", "text")
        assert CITE_ERROR_PREFIX in result
        assert "task scope" in result
        mock_get_info.assert_not_called()

    @patch("unique_sdk.Content.get_info")
    def test_cont_id_gated_before_title_fetch_without_filter(
        self, mock_get_info: MagicMock, state: ShellState, workspace: Path
    ):
        """Even without a per-message filter, cite enforces scope on a cont_ id
        (matching read's cont_ fast-path) and denies *before* resolving the
        title, so no Content.get_info probes the KB. See UN-21780.
        """
        with patch.object(
            ShellState, "is_content_within_workspace", return_value=False
        ):
            result = cmd_cite_file(state, "cont_blocked", "1", "text")
        assert CITE_ERROR_PREFIX in result
        assert "task scope" in result
        mock_get_info.assert_not_called()

    def test_metadata_filter_allows_chat_attached_file(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        """Chat-attached files stay citeable even when the filter excludes them."""
        state.workspace_metadata_filter = {
            "path": ["contentId"],
            "operator": "in",
            "value": ["cont_other"],
        }
        result = cmd_cite_file(state, "report.pdf", "1", "text")
        assert CITE_ERROR_PREFIX not in result
        assert "[filesource1] -> report.pdf page 1" in result


class TestNonPaginated:
    @pytest.mark.parametrize(
        "filename",
        [
            "data.xlsx",
            "data.xls",
            "rows.csv",
            "notes.txt",
            "page.html",
            "page.htm",
            "readme.md",
            "chart.PNG",
            "scan.jpeg",
            "logo.webp",
        ],
    )
    def test_known_non_paginated_suffixes(self, filename: str):
        assert _is_non_paginated(filename) is True

    @pytest.mark.parametrize(
        "filename", ["report.pdf", "deck.pptx", "cont_abc123", "notes.docx"]
    )
    def test_paginated_or_unknown_suffixes(self, filename: str):
        assert _is_non_paginated(filename) is False

    def test_pages_on_non_paginated_returns_error_and_writes_nothing(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "data.xlsx", "2", "text")

        assert CITE_ERROR_PREFIX in result
        assert "non-paginated" in result
        assert "omit --pages" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        assert not manifest.exists()

    def test_whole_file_non_paginated_is_allowed(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "data.xlsx", None, "text")

        assert "[filesource1] -> data.xlsx page 0" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["page"] == 0

    def test_pages_on_paginated_pdf_still_works(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "2", "text")

        assert "[filesource1] -> report.pdf page 2" in result


class TestNormalizeReadMethod:
    @pytest.mark.parametrize("method", READ_METHODS)
    def test_canonical_values_pass_through(self, method: str):
        assert _normalize_read_method(method) == method

    def test_case_insensitive(self):
        assert _normalize_read_method("Text") == "text"
        assert _normalize_read_method("  Vision ") == "vision"

    @pytest.mark.parametrize(
        ("alias", "expected"),
        [
            ("pdftotext", "text"),
            ("pymupdf", "text"),
            ("fitz", "text"),
            ("mupdf", "text"),
            ("pdfminer", "text"),
            ("markitdown", "text"),
            ("image", "vision"),
            ("ocr", "vision"),
            ("render", "vision"),
            ("read", "indexed"),
            ("search", "indexed"),
        ],
    )
    def test_aliases_normalize(self, alias: str, expected: str):
        assert _normalize_read_method(alias) == expected

    def test_missing_returns_none(self):
        assert _normalize_read_method(None) is None
        assert _normalize_read_method("") is None
        assert _normalize_read_method("   ") is None

    def test_unknown_returns_none(self):
        assert _normalize_read_method("magic") is None


class TestReadMethodEnforcement:
    def test_missing_read_method_writes_nothing(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "3", None)

        assert CITE_ERROR_PREFIX in result
        assert "--read-method" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        assert not manifest.exists()

    def test_invalid_read_method_writes_nothing(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "3", "telepathy")

        assert CITE_ERROR_PREFIX in result
        assert "--read-method" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        assert not manifest.exists()

    def test_alias_persisted_canonical(
        self, state: ShellState, workspace_with_manifest: Path
    ):
        result = cmd_cite_file(state, "report.pdf", "3", "fitz")

        assert "[filesource1] -> report.pdf page 3" in result
        manifest = workspace_with_manifest / ".unique" / "file-refs.jsonl"
        lines = [json.loads(line) for line in manifest.read_text().splitlines()]
        assert lines[0]["readMethod"] == "text"
