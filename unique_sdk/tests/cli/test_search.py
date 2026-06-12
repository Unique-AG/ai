"""Tests for the unique-cli search subcommand and its citation manifest.

Structured to mirror ``tests/cli/test_web_search.py`` from PR #1733 — both
commands write to ``.unique/`` JSONL manifests via shared helpers in
``unique_sdk.cli.commands._citation_manifest``, so the test layout stays
symmetric.

Unlike web-search, which dedupes manifest entries by URL, KB search
appends one manifest line per result every time. That is intentional:
each ContentChunk is a distinct citation target (different page range,
different chunk_id, ...), so URL-based dedup would collapse chunks that
the runner expects to keep separate. The
``test_kb_does_not_dedupe_repeated_results`` case below exists so future
readers don't accidentally introduce parity with the web-search path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import unique_sdk
from unique_sdk.cli.commands._citation_manifest import (
    UnsafeRefsLogPathError,
    _append_turn_refs_manifest_entry,
    _assert_safe_refs_log_path,
    _locked_turn_refs_manifest,
    _read_turn_refs_manifest,
)
from unique_sdk.cli.commands.search import (
    SEARCH_ERROR_PREFIX,
    _build_metadata_filter,
    _format_source_block,
    _result_to_chunk_payload,
    cmd_search,
    is_error_output,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState


def _config() -> Config:
    return Config(
        user_id="u1",
        company_id="c1",
        api_key="key",
        app_id="app",
        api_base="https://example.com",
    )


def _state(path: str = "/", scope_id: str | None = None) -> ShellState:
    s = ShellState(_config())
    s._path = path
    s._scope_id = scope_id
    return s


@pytest.fixture(autouse=True)
def _isolate_kb_search_refs_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin every test's cwd into ``tmp_path``.

    ``cmd_search`` defaults the manifest path to
    ``<cwd>/.unique/kb-search-refs.jsonl``; isolating cwd keeps concurrent
    tests from clobbering each other's manifest and matches the autouse
    fixture pattern in ``test_web_search.py``.
    """
    monkeypatch.chdir(tmp_path)


def _make_search_result(
    *,
    content_id: str = "cont_abc",
    chunk_id: str = "chunk_xyz",
    text: str = "...the quarterly revenue analysis shows a 15% increase...",
    order: int = 0,
    key: str | None = "annual-report.pdf",
    url: str | None = None,
    title: str | None = "annual-report.pdf",
    start_page: int | None = 12,
    end_page: int | None = 13,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = "2026-01-01T00:00:00Z",
    updated_at: str | None = "2026-01-02T00:00:00Z",
) -> MagicMock:
    """Stand-in for a ``unique_sdk.Search`` result with the attrs we read."""
    result = MagicMock()
    result.id = content_id
    result.chunkId = chunk_id
    result.text = text
    result.order = order
    result.key = key
    result.url = url
    result.title = title
    result.startPage = start_page
    result.endPage = end_page
    result.metadata = metadata
    result.createdAt = created_at
    result.updatedAt = updated_at
    return result


class TestBuildMetadataFilter:
    def test_none_returns_none(self) -> None:
        assert _build_metadata_filter(None, None) is None

    def test_folder_only(self) -> None:
        result = _build_metadata_filter("scope_abc", None)
        assert result is not None
        assert result["path"] == ["folderIdPath"]
        assert "scope_abc" in result["value"]

    def test_metadata_only(self) -> None:
        result = _build_metadata_filter(None, [("dept", "Legal")])
        assert result is not None
        assert result["path"] == ["dept"]
        assert result["value"] == "Legal"

    def test_combined_is_anded(self) -> None:
        result = _build_metadata_filter("scope_abc", [("dept", "Legal")])
        assert result is not None
        assert "and" in result


class TestFormatSourceBlock:
    def test_block_shape(self) -> None:
        block = _format_source_block(1, _make_search_result())
        assert block.startswith("<source1>\n")
        assert block.endswith("\n</source1>")
        assert "<|document|>annual-report.pdf</|document|>" in block
        assert "<|page|>12-13</|page|>" in block
        assert "<|info|>cont_abc</|info|>" in block

    def test_single_page_block(self) -> None:
        block = _format_source_block(3, _make_search_result(start_page=5, end_page=5))
        assert "<|page|>5</|page|>" in block

    def test_block_without_pages(self) -> None:
        block = _format_source_block(
            7, _make_search_result(start_page=None, end_page=None)
        )
        assert "<|page|>" not in block

    def test_block_uses_key_when_title_missing(self) -> None:
        block = _format_source_block(
            2, _make_search_result(title=None, key="fallback.txt")
        )
        assert "<|document|>fallback.txt</|document|>" in block

    def test_block_falls_back_to_content_id(self) -> None:
        block = _format_source_block(
            4, _make_search_result(title=None, key=None, content_id="cont_only")
        )
        assert "<|document|>content cont_only</|document|>" in block


class TestResultToChunkPayload:
    def test_emits_all_camelcase_keys(self) -> None:
        payload = _result_to_chunk_payload(
            _make_search_result(
                metadata={"department": "Finance"},
            )
        )
        assert payload == {
            "id": "cont_abc",
            "chunkId": "chunk_xyz",
            "text": "...the quarterly revenue analysis shows a 15% increase...",
            "order": 0,
            "key": "annual-report.pdf",
            "url": None,
            "title": "annual-report.pdf",
            "startPage": 12,
            "endPage": 13,
            "metadata": {"department": "Finance"},
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        }

    def test_non_dict_metadata_is_dropped(self) -> None:
        result = _make_search_result(metadata="not-a-dict")  # type: ignore[arg-type]
        assert _result_to_chunk_payload(result)["metadata"] is None


class TestCmdSearchCitations:
    @patch("unique_sdk.Search.create")
    def test_happy_path_writes_block_and_manifest(self, mock: MagicMock) -> None:
        mock.return_value = [_make_search_result()]

        out = cmd_search(_state(), "quarterly revenue")

        assert "Found 1 result(s):" in out
        assert "<source1>" in out
        assert "</source1>" in out
        assert "<|document|>annual-report.pdf</|document|>" in out
        assert "<|page|>12-13</|page|>" in out
        assert "<|info|>cont_abc</|info|>" in out

        manifest = Path.cwd() / ".unique" / "kb-search-refs.jsonl"
        lines = manifest.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry == {
            "id": "cont_abc",
            "chunkId": "chunk_xyz",
            "text": "...the quarterly revenue analysis shows a 15% increase...",
            "order": 0,
            "key": "annual-report.pdf",
            "url": None,
            "title": "annual-report.pdf",
            "startPage": 12,
            "endPage": 13,
            "metadata": None,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        }

    @patch("unique_sdk.Search.create")
    def test_numbering_continues_across_two_calls(self, mock: MagicMock) -> None:
        mock.side_effect = [
            [
                _make_search_result(content_id="cont_a", chunk_id="chunk_a"),
                _make_search_result(content_id="cont_b", chunk_id="chunk_b"),
            ],
            [
                _make_search_result(content_id="cont_c", chunk_id="chunk_c"),
            ],
        ]

        first = cmd_search(_state(), "query one")
        second = cmd_search(_state(), "query two")

        assert "<source1>" in first
        assert "<source2>" in first
        assert "<source3>" in second

        manifest = Path.cwd() / ".unique" / "kb-search-refs.jsonl"
        ids = [
            json.loads(line)["id"]
            for line in manifest.read_text(encoding="utf-8").splitlines()
        ]
        assert ids == ["cont_a", "cont_b", "cont_c"]

    @patch("unique_sdk.Search.create")
    def test_kb_does_not_dedupe_repeated_results(self, mock: MagicMock) -> None:
        # NOTE: unique-cli web-search dedupes results by URL so the same URL
        # keeps the same `websourceN`. KB search intentionally does NOT
        # dedupe — each ContentChunk is its own citation target (page
        # range, chunk_id differ in general). If a future change tries to
        # add URL- or id-based dedup here, drop it: the runner relies on
        # one manifest line per `<sourceN>` block emitted to the LLM.
        same = _make_search_result(content_id="cont_dup", chunk_id="chunk_dup")
        mock.return_value = [same, same]

        out = cmd_search(_state(), "duplicate")

        assert "<source1>" in out
        assert "<source2>" in out
        manifest = Path.cwd() / ".unique" / "kb-search-refs.jsonl"
        assert len(manifest.read_text(encoding="utf-8").splitlines()) == 2

    @patch("unique_sdk.Search.create")
    def test_malformed_existing_manifest_lines_are_skipped(
        self, mock: MagicMock
    ) -> None:
        manifest_dir = Path.cwd() / ".unique"
        manifest_dir.mkdir()
        manifest = manifest_dir / "kb-search-refs.jsonl"
        manifest.write_text(
            "\n".join(
                [
                    json.dumps({"id": "cont_pre", "text": "previous"}),
                    "not-json",
                    "{not even close}",
                    "",
                    json.dumps({"id": "cont_pre2", "text": "still here"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        mock.return_value = [_make_search_result(content_id="cont_new")]
        out = cmd_search(_state(), "query")

        # 2 valid pre-existing entries + 1 new = the new block must be source3.
        assert "<source3>" in out
        ids = [
            json.loads(line)["id"]
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("{") and "id" in line
        ]
        assert ids[-1] == "cont_new"

    @patch("unique_sdk.Search.create")
    def test_empty_results_no_manifest_write(self, mock: MagicMock) -> None:
        mock.return_value = []
        out = cmd_search(_state(), "no hits")
        assert "No results found" in out
        assert not (Path.cwd() / ".unique").exists()

    @patch("unique_sdk.Search.create")
    def test_api_error_returns_prefix_and_writes_nothing(self, mock: MagicMock) -> None:
        mock.side_effect = ValueError("boom")
        out = cmd_search(_state(), "fail")
        assert out.startswith(SEARCH_ERROR_PREFIX)
        assert "boom" in out
        assert not (Path.cwd() / ".unique").exists()

    @patch("unique_sdk.Search.create")
    def test_symlinked_unique_dir_returns_error_and_skips_write(
        self, mock: MagicMock, tmp_path: Path
    ) -> None:
        # Replace .unique with a symlink to a sibling dir to exercise the
        # _assert_safe_refs_log_path guard. The command should refuse to
        # write and surface a "search: ..." error string.
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        unique_dir = Path.cwd() / ".unique"
        os.symlink(elsewhere, unique_dir, target_is_directory=True)

        mock.return_value = [_make_search_result()]
        out = cmd_search(_state(), "query")

        assert out.startswith(SEARCH_ERROR_PREFIX)
        # No manifest in the real target dir either — the safety check
        # fires before the write happens.
        assert not (elsewhere / "kb-search-refs.jsonl").exists()


class TestIsErrorOutput:
    def test_error_string_is_error(self) -> None:
        assert is_error_output(f"{SEARCH_ERROR_PREFIX} something failed") is True

    def test_normal_output_is_not_error(self) -> None:
        assert is_error_output("Found 1 result(s):\n<source1>...</source1>") is False


class TestCitationManifestHelpers:
    """Direct tests of the shared `_citation_manifest` module."""

    def test_read_skips_blank_and_invalid_lines(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".unique" / "kb-search-refs.jsonl"
        manifest.parent.mkdir()
        manifest.write_text(
            "\n".join(
                [
                    "",
                    "not json",
                    json.dumps({"id": "a"}),
                    json.dumps(["array", "is", "skipped"]),
                    json.dumps({"id": "b"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        entries = _read_turn_refs_manifest(manifest)
        assert [e["id"] for e in entries] == ["a", "b"]

    def test_append_creates_parent_dir(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".unique" / "kb-search-refs.jsonl"
        _append_turn_refs_manifest_entry(manifest, {"id": "first"})
        _append_turn_refs_manifest_entry(manifest, {"id": "second"})
        lines = manifest.read_text(encoding="utf-8").splitlines()
        assert [json.loads(line)["id"] for line in lines] == ["first", "second"]

    def test_assert_safe_rejects_symlinked_parent(self, tmp_path: Path) -> None:
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        link_dir = tmp_path / "link_to_real"
        os.symlink(real_dir, link_dir, target_is_directory=True)
        manifest = link_dir / "kb-search-refs.jsonl"

        with pytest.raises(UnsafeRefsLogPathError):
            _assert_safe_refs_log_path(manifest)

    def test_locked_manifest_runs_critical_section(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".unique" / "kb-search-refs.jsonl"
        with _locked_turn_refs_manifest(manifest, lock_filename="kb-search-refs.lock"):
            _append_turn_refs_manifest_entry(manifest, {"id": "under-lock"})
        lock_file = manifest.parent / "kb-search-refs.lock"
        assert lock_file.exists()
        assert json.loads(manifest.read_text(encoding="utf-8").splitlines()[0]) == {
            "id": "under-lock"
        }


class TestContentChunkRoundTrip:
    """Verify the manifest line shape rehydrates as a ``ContentChunk``.

    Skipped when ``unique_toolkit`` is not installed in the test
    environment — the SDK package on CI does not pull it in, so this
    test depends on having the workspace toolkit available locally.
    """

    def test_manifest_line_rehydrates_as_content_chunk(self) -> None:
        pytest.importorskip("unique_toolkit")
        from unique_toolkit.content.schemas import ContentChunk

        payload = _result_to_chunk_payload(
            _make_search_result(
                metadata={"key": "annual-report.pdf", "mimeType": "application/pdf"},
            )
        )
        line = json.dumps(payload, default=str)
        chunk = ContentChunk.model_validate(json.loads(line))

        assert chunk.id == "cont_abc"
        assert chunk.chunk_id == "chunk_xyz"
        assert chunk.text.startswith("...the quarterly")
        assert chunk.title == "annual-report.pdf"
        assert chunk.start_page == 12
        assert chunk.end_page == 13
        assert chunk.metadata is not None
        assert chunk.metadata.key == "annual-report.pdf"
        assert chunk.metadata.mime_type == "application/pdf"


class TestCmdSearchCallShapes:
    """Existing happy-path call-shape coverage, kept here so the new module
    is self-contained alongside test_commands.py (no extra surface)."""

    @patch("unique_sdk.Search.create")
    def test_scope_id_passed_through(self, mock: MagicMock) -> None:
        mock.return_value = []
        cmd_search(_state("/R", "scope_r"), "q")
        assert mock.call_args[1]["scopeIds"] == ["scope_r"]

    @patch("unique_sdk.Search.create")
    def test_uses_workspace_scope_ids_when_no_folder(self, mock: MagicMock) -> None:
        mock.return_value = []
        s = _state()
        s.workspace_scope_ids = ["scope_ws1", "scope_ws2"]
        cmd_search(s, "q")
        assert mock.call_args[1]["scopeIds"] == ["scope_ws1", "scope_ws2"]

    @patch("unique_sdk.Search.create")
    def test_workspace_metadata_filter_used_when_present(self, mock: MagicMock) -> None:
        mock.return_value = []
        s = _state()
        rule = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "uniquepathid://scope_fund_a",
        }
        s.workspace_metadata_filter = rule
        cmd_search(s, "q")
        assert mock.call_args[1]["metaDataFilter"] == rule
        assert "scopeIds" not in mock.call_args[1]

    @patch("unique_sdk.Search.create")
    def test_workspace_metadata_filter_overrides_workspace_scope_ids(
        self, mock: MagicMock
    ) -> None:
        mock.return_value = []
        s = _state()
        s.workspace_scope_ids = ["scope_ws_default"]
        rule = {
            "or": [
                {"path": ["folderIdPath"], "operator": "contains", "value": "x"},
                {"path": ["contentId"], "operator": "in", "value": ["cont_1"]},
            ]
        }
        s.workspace_metadata_filter = rule
        cmd_search(s, "q")
        assert mock.call_args[1]["metaDataFilter"] == rule
        assert "scopeIds" not in mock.call_args[1]

    @patch("unique_sdk.Search.create")
    def test_explicit_metadata_arg_is_anded_with_workspace_filter(
        self, mock: MagicMock
    ) -> None:
        """--metadata narrows the per-message scope; it must never escape it."""
        mock.return_value = []
        s = _state()
        wmf = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "uniquepathid://scope_fund_a",
        }
        s.workspace_metadata_filter = wmf
        cmd_search(s, "q", metadata=[("dept", "Legal")])
        sent = mock.call_args[1]["metaDataFilter"]
        assert sent["and"][0] == wmf
        assert sent["and"][1]["path"] == ["dept"]
        assert sent["and"][1]["value"] == "Legal"

    @patch("unique_sdk.Search.create")
    def test_cwd_scope_id_keeps_workspace_filter(self, mock: MagicMock) -> None:
        """A cwd folder narrows via scopeIds; the per-message filter stays on."""
        mock.return_value = []
        s = _state("/R", "scope_r")
        wmf = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "uniquepathid://scope_fund_a",
        }
        s.workspace_metadata_filter = wmf
        cmd_search(s, "q")
        assert mock.call_args[1]["scopeIds"] == ["scope_r"]
        assert mock.call_args[1]["metaDataFilter"] == wmf

    @patch("unique_sdk.cli.commands.search._resolve_folder_to_scope_id")
    @patch("unique_sdk.Search.create")
    def test_explicit_folder_arg_keeps_workspace_filter(
        self, mock: MagicMock, mock_resolve: MagicMock
    ) -> None:
        """--folder must not drop the per-message scope (escape vector)."""
        mock.return_value = []
        mock_resolve.return_value = "scope_other"
        s = _state()
        wmf = {
            "path": ["folderIdPath"],
            "operator": "contains",
            "value": "uniquepathid://scope_fund_a",
        }
        s.workspace_metadata_filter = wmf
        cmd_search(s, "q", folder="/Other")
        assert mock.call_args[1]["scopeIds"] == ["scope_other"]
        assert mock.call_args[1]["metaDataFilter"] == wmf

    @patch("unique_sdk.Search.create")
    def test_api_error_includes_prefix(self, mock: MagicMock) -> None:
        mock.side_effect = unique_sdk.APIError("oops")
        out = cmd_search(_state(), "q")
        assert out.startswith(SEARCH_ERROR_PREFIX)
        assert "oops" in out
