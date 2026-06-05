"""Tests for unique-cli read command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unique_sdk.cli.commands.read import READ_ERROR_PREFIX, cmd_read, is_error_output
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


class TestIsErrorOutput:
    def test_error_string(self) -> None:
        assert is_error_output(f"{READ_ERROR_PREFIX} something went wrong")

    def test_normal_output(self) -> None:
        assert not is_error_output("Content: doc.pdf (cont_abc123) — 5 chunk(s)")
