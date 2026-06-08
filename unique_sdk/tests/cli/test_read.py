"""Tests for unique-cli read command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unique_sdk.cli.commands.read import (
    READ_ERROR_PREFIX,
    _chunk_in_page_range,
    cmd_read,
    is_error_output,
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


def _make_content(
    cont_id: str = "cont_abc123",
    title: str = "annual-report.pdf",
    chunks: list[dict] | None = None,
) -> MagicMock:
    content = MagicMock()
    content.id = cont_id
    content.title = title
    content.key = title
    content.chunks = chunks
    return content


class TestCmdRead:
    def test_rejects_non_cont_id(self, state: ShellState) -> None:
        output = cmd_read(state, "not_a_content_id")
        assert is_error_output(output)
        assert "cont_" in output

    def test_not_found_returns_error(self, state: ShellState) -> None:
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search", return_value=[]
        ):
            output = cmd_read(state, "cont_missing")
        assert is_error_output(output)
        assert "cont_missing" in output

    def test_api_error_returns_error(self, state: ShellState) -> None:
        import unique_sdk

        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            side_effect=unique_sdk.APIError("boom", http_status=500, headers={}),
        ):
            output = cmd_read(state, "cont_abc123")
        assert is_error_output(output)

    def test_empty_chunks_reports_not_indexed(self, state: ShellState) -> None:
        content = _make_content(chunks=[])
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert not is_error_output(output)
        assert "ingesting" in output.lower() or "no indexed" in output.lower()

    def test_none_chunks_reports_not_indexed(self, state: ShellState) -> None:
        content = _make_content(chunks=None)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert not is_error_output(output)
        assert "ingesting" in output.lower() or "no indexed" in output.lower()

    def test_returns_chunks_as_plain_text(self, state: ShellState) -> None:
        chunks = [
            {
                "id": "ch1",
                "text": "First chunk text.",
                "order": 1,
                "startPage": 1,
                "endPage": 1,
            },
            {
                "id": "ch2",
                "text": "Second chunk text.",
                "order": 2,
                "startPage": 2,
                "endPage": 3,
            },
        ]
        content = _make_content(chunks=chunks)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert not is_error_output(output)
        assert "First chunk text." in output
        assert "Second chunk text." in output
        assert "[p.1]" in output
        assert "[p.2-3]" in output

    def test_start_page_only_gets_page_label(self, state: ShellState) -> None:
        chunks = [
            {
                "id": "ch1",
                "text": "Single page chunk.",
                "order": 1,
                "startPage": 4,
                "endPage": None,
            }
        ]
        content = _make_content(chunks=chunks)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert "[p.4] Single page chunk." in output

    def test_page_zero_gets_page_label(self, state: ShellState) -> None:
        chunks = [
            {
                "id": "ch1",
                "text": "Cover page.",
                "order": 1,
                "startPage": 0,
                "endPage": 0,
            }
        ]
        content = _make_content(chunks=chunks)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert "[p.0] Cover page." in output

    def test_chunks_sorted_by_order(self, state: ShellState) -> None:
        chunks = [
            {"id": "ch2", "text": "B", "order": 2, "startPage": None, "endPage": None},
            {"id": "ch1", "text": "A", "order": 1, "startPage": None, "endPage": None},
        ]
        content = _make_content(chunks=chunks)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert output.index("A") < output.index("B")

    def test_chunks_with_null_order_handled(self, state: ShellState) -> None:
        chunks = [
            {
                "id": "ch1",
                "text": "Only chunk.",
                "order": None,
                "startPage": None,
                "endPage": None,
            }
        ]
        content = _make_content(chunks=chunks)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert "Only chunk." in output

    def test_header_contains_title_and_id(self, state: ShellState) -> None:
        chunks = [
            {
                "id": "ch1",
                "text": "Some text.",
                "order": 1,
                "startPage": 1,
                "endPage": 1,
            }
        ]
        content = _make_content(title="my-doc.pdf", chunks=chunks)
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ):
            output = cmd_read(state, "cont_abc123")
        assert "my-doc.pdf" in output
        assert "cont_abc123" in output

    def test_calls_content_search_with_id_filter(self, state: ShellState) -> None:
        content = _make_content(chunks=[])
        with patch(
            "unique_sdk.cli.commands.read.unique_sdk.Content.search",
            return_value=[content],
        ) as mock_search:
            cmd_read(state, "cont_abc123")
        mock_search.assert_called_once_with(
            user_id="user_test",
            company_id="comp_test",
            where={"id": {"equals": "cont_abc123"}},
        )

    def test_read_outside_workspace_blocked(self, state: ShellState) -> None:
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        output = cmd_read(state, "cont_abc123")
        assert is_error_output(output)
        assert "permission denied" in output

    @patch("unique_sdk.Content.get_info")
    def test_read_content_id_outside_workspace_blocked(
        self, mock_info: MagicMock, state: ShellState
    ) -> None:
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_other_tenant"}]}
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        output = cmd_read(state, "cont_outside")
        assert is_error_output(output)
        assert "permission denied" in output

    @patch("unique_sdk.cli.commands.read.unique_sdk.Content.search")
    @patch("unique_sdk.Content.get_info")
    def test_read_content_id_within_workspace_allowed(
        self,
        mock_info: MagicMock,
        mock_search: MagicMock,
        state: ShellState,
    ) -> None:
        mock_info.return_value = {"contentInfo": [{"ownerId": "scope_ws"}]}
        content = _make_content(
            cont_id="cont_inside",
            chunks=[
                {
                    "id": "ch1",
                    "text": "Allowed text.",
                    "order": 1,
                    "startPage": None,
                    "endPage": None,
                }
            ],
        )
        mock_search.return_value = [content]
        state.workspace_scope_ids = ["scope_ws"]
        state._workspace_scope_paths = ["/Workspace"]
        output = cmd_read(state, "cont_inside")
        assert "permission denied" not in output
        assert "Allowed text." in output


class TestChunkInPageRange:
    def test_single_page_overlap(self) -> None:
        spanning = {"startPage": 2, "endPage": 4}
        assert _chunk_in_page_range(spanning, 3, 3)
        assert _chunk_in_page_range(spanning, 2, 2)
        assert _chunk_in_page_range(spanning, 4, 4)
        assert not _chunk_in_page_range(spanning, 5, 5)
        assert not _chunk_in_page_range(spanning, 1, 1)

    def test_open_ended_ranges(self) -> None:
        chunk = {"startPage": 5, "endPage": 5}
        assert _chunk_in_page_range(chunk, 5, None)
        assert _chunk_in_page_range(chunk, None, 5)
        assert not _chunk_in_page_range(chunk, 6, None)
        assert not _chunk_in_page_range(chunk, None, 4)

    def test_chunk_without_pages_excluded(self) -> None:
        assert not _chunk_in_page_range({"startPage": None, "endPage": None}, 1, 3)

    def test_start_only_chunk(self) -> None:
        assert _chunk_in_page_range({"startPage": 4, "endPage": None}, 4, 4)
        assert not _chunk_in_page_range({"startPage": 4, "endPage": None}, 5, 5)


def _read(state: ShellState, content: MagicMock, *args, **kwargs) -> str:
    with patch(
        "unique_sdk.cli.commands.read.unique_sdk.Content.search",
        return_value=[content],
    ):
        return cmd_read(state, "cont_abc123", *args, **kwargs)


class TestCmdReadPageRange:
    def _content(self) -> MagicMock:
        return _make_content(
            chunks=[
                {"id": "c1", "text": "first", "order": 0, "startPage": 1, "endPage": 1},
                {
                    "id": "c2",
                    "text": "second",
                    "order": 1,
                    "startPage": 5,
                    "endPage": 5,
                },
                {"id": "c3", "text": "third", "order": 2, "startPage": 9, "endPage": 9},
            ]
        )

    def test_filters_to_range(self, state: ShellState) -> None:
        output = _read(state, self._content(), from_page=4, to_page=6)
        assert "second" in output
        assert "first" not in output
        assert "third" not in output

    def test_single_page(self, state: ShellState) -> None:
        output = _read(state, self._content(), from_page=1, to_page=1)
        assert "first" in output
        assert "second" not in output

    def test_no_match_in_range(self, state: ShellState) -> None:
        output = _read(state, self._content(), from_page=50, to_page=60)
        assert not is_error_output(output)
        assert "No indexed chunks found in page range" in output

    def test_invalid_range(self, state: ShellState) -> None:
        output = cmd_read(state, "cont_abc123", from_page=9, to_page=3)
        assert is_error_output(output)
        assert "invalid page range" in output

    def test_excludes_unpaged_chunks_when_filtering(self, state: ShellState) -> None:
        content = _make_content(
            chunks=[
                {"id": "c1", "text": "paged", "order": 0, "startPage": 2, "endPage": 2},
                {
                    "id": "c2",
                    "text": "unpaged",
                    "order": 1,
                    "startPage": None,
                    "endPage": None,
                },
            ]
        )
        output = _read(state, content, from_page=2, to_page=2)
        assert "paged" in output
        assert "unpaged" not in output

    def test_max_chars_truncates(self, state: ShellState) -> None:
        content = _make_content(
            chunks=[
                {
                    "id": "c1",
                    "text": "x" * 500,
                    "order": 0,
                    "startPage": 1,
                    "endPage": 1,
                }
            ]
        )
        output = _read(state, content, max_chars=50)
        assert "truncated at 50 chars" in output


class TestIsErrorOutput:
    def test_error_string(self) -> None:
        assert is_error_output(f"{READ_ERROR_PREFIX} something went wrong")

    def test_normal_output(self) -> None:
        assert not is_error_output("Content: doc.pdf (cont_abc123) — 5 chunk(s)")
