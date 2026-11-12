"""Tests for ``unique-cli search`` with several queries in one call."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

import unique_sdk
from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.search import (
    MAX_SEARCH_QUERIES,
    SEARCH_CONCURRENCY,
    SEARCH_ERROR_PREFIX,
    cmd_search,
    cmd_search_many,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState


def _state(path: str = "/", scope_id: str | None = None) -> ShellState:
    state = ShellState(
        Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
    )
    state._path = path
    state._scope_id = scope_id
    return state


@pytest.fixture(autouse=True)
def _isolate_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _result(content_id: str) -> MagicMock:
    result = MagicMock()
    result.id = content_id
    result.chunkId = f"chunk_{content_id}"
    result.text = f"text of {content_id}"
    result.order = 0
    result.key = f"{content_id}.pdf"
    result.url = None
    result.title = f"{content_id}.pdf"
    result.startPage = 1
    result.endPage = 1
    result.metadata = None
    result.createdAt = None
    result.updatedAt = None
    return result


IDS_BY_QUERY: dict[str, list[str]] = {
    "revenue": ["cont_r1", "cont_r2"],
    "margin": ["cont_m1"],
    "headcount": ["cont_h1", "cont_h2", "cont_h3"],
}


def _search_by_query(
    ids_by_query: dict[str, list[str]],
    *,
    delay_by_query: dict[str, float] | None = None,
    fail_queries: frozenset[str] = frozenset(),
) -> Callable[..., list[MagicMock]]:
    delays = delay_by_query or {}

    def _search(**kwargs: Any) -> list[MagicMock]:
        query = kwargs["searchString"]
        time.sleep(delays.get(query, 0.0))
        if query in fail_queries:
            raise unique_sdk.APIError(f"upstream failed for {query}")
        return [_result(content_id) for content_id in ids_by_query[query]]

    return _search


def _manifest_ids(tmp_path: Path) -> list[str]:
    manifest = tmp_path / ".unique" / "kb-search-refs.jsonl"
    return [
        json.loads(line)["id"]
        for line in manifest.read_text(encoding="utf-8").splitlines()
    ]


class TestMultiQueryOutput:
    @patch("unique_sdk.Search.create")
    def test_blocks_follow_query_order_not_completion_order(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(
            IDS_BY_QUERY, delay_by_query={"revenue": 0.2}
        )

        out = cmd_search_many(_state(), ["revenue", "margin", "headcount"])

        assert out.index("=== query 1/3: 'revenue' ===") < out.index(
            "=== query 2/3: 'margin' ==="
        )
        assert out.index("=== query 2/3: 'margin' ===") < out.index(
            "=== query 3/3: 'headcount' ==="
        )

    @patch("unique_sdk.Search.create")
    def test_source_numbers_follow_query_order_and_match_the_manifest(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(
            IDS_BY_QUERY, delay_by_query={"revenue": 0.2}
        )

        out = cmd_search_many(_state(), ["revenue", "margin", "headcount"])

        expected = ["cont_r1", "cont_r2", "cont_m1", "cont_h1", "cont_h2", "cont_h3"]
        for number, content_id in enumerate(expected, start=1):
            block_start = out.index(f"<source{number}>")
            assert out.index(f"<|info|>{content_id}</|info|>") > block_start
        assert _manifest_ids(tmp_path) == expected

    @patch("unique_sdk.Search.create")
    def test_numbering_continues_after_an_earlier_call_in_the_turn(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        cmd_search(_state(), "margin")
        out = cmd_search_many(_state(), ["revenue", "headcount"])

        assert "<source1>" not in out
        assert "<source2>" in out
        assert "<source6>" in out
        assert len(_manifest_ids(tmp_path)) == 6

    @patch("unique_sdk.Search.create")
    def test_query_without_results_says_so(self, mock_search: MagicMock) -> None:
        mock_search.side_effect = _search_by_query({**IDS_BY_QUERY, "empty": []})

        out = cmd_search_many(_state(), ["empty", "margin"])

        assert "=== query 1/2: 'empty' ===\nNo results found." in out
        assert "<source1>" in out


class TestMultiQueryFailures:
    @patch("unique_sdk.Search.create")
    def test_failed_query_keeps_the_others(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(
            IDS_BY_QUERY, fail_queries=frozenset({"margin"})
        )

        out = cmd_search_many(_state(), ["revenue", "margin", "headcount"])

        assert not out.startswith(SEARCH_ERROR_PREFIX)
        assert "=== query 2/3: 'margin' ===\nERROR: search:" in out
        assert "upstream failed for margin" in out
        assert out.endswith("1 of 3 queries failed.")
        assert _manifest_ids(tmp_path) == [
            "cont_r1",
            "cont_r2",
            "cont_h1",
            "cont_h2",
            "cont_h3",
        ]

    @patch("unique_sdk.Search.create")
    def test_all_queries_failing_returns_an_error_output(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(
            IDS_BY_QUERY, fail_queries=frozenset({"revenue", "margin"})
        )

        out = cmd_search_many(_state(), ["revenue", "margin"])

        assert out.startswith(f"{SEARCH_ERROR_PREFIX} all 2 queries failed.")

    @patch("unique_sdk.Search.create")
    def test_too_many_queries_is_rejected_before_any_request(
        self, mock_search: MagicMock
    ) -> None:
        queries = [f"q{i}" for i in range(MAX_SEARCH_QUERIES + 1)]

        out = cmd_search_many(_state(), queries)

        assert out.startswith(SEARCH_ERROR_PREFIX)
        assert "too many queries" in out
        mock_search.assert_not_called()

    @patch("unique_sdk.Search.create")
    @patch("unique_sdk.Folder.get_info")
    def test_unresolvable_folder_is_rejected_before_any_request(
        self, mock_info: MagicMock, mock_search: MagicMock
    ) -> None:
        mock_info.side_effect = unique_sdk.APIError("Folder /Nope not found")

        out = cmd_search_many(_state(), ["revenue", "margin"], folder="/Nope")

        assert out.startswith(SEARCH_ERROR_PREFIX)
        mock_search.assert_not_called()


class TestMultiQueryRequests:
    @patch("unique_sdk.Search.create")
    @patch("unique_sdk.Folder.get_info")
    def test_every_request_carries_the_shared_filters(
        self, mock_info: MagicMock, mock_search: MagicMock
    ) -> None:
        mock_info.return_value = {"id": "scope_q1"}
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        cmd_search_many(
            _state(),
            ["revenue", "margin"],
            folder="/Reports/Q1",
            metadata=[("department", "Finance")],
            limit=25,
        )

        mock_info.assert_called_once()
        calls = [call.kwargs for call in mock_search.call_args_list]
        assert sorted(call["searchString"] for call in calls) == ["margin", "revenue"]
        for call in calls:
            assert call["searchType"] == "COMBINED"
            assert call["limit"] == 25
            assert call["scopeIds"] == ["scope_q1"]
            assert "metaDataFilter" in call
            assert call["user_id"] == "u1"
            assert call["company_id"] == "c1"

    @patch("unique_sdk.Search.create")
    def test_requests_overlap_but_stay_within_the_bound(
        self, mock_search: MagicMock
    ) -> None:
        queries = [f"q{i}" for i in range(MAX_SEARCH_QUERIES)]
        ids = {query: [f"cont_{query}"] for query in queries}
        in_flight = 0
        peak = 0
        lock = threading.Lock()
        inner = _search_by_query(ids, delay_by_query=dict.fromkeys(queries, 0.1))

        def _tracked(**kwargs: Any) -> list[MagicMock]:
            nonlocal in_flight, peak
            with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            try:
                return inner(**kwargs)
            finally:
                with lock:
                    in_flight -= 1

        mock_search.side_effect = _tracked

        out = cmd_search_many(_state(), queries)

        assert not out.startswith(SEARCH_ERROR_PREFIX)
        assert 2 <= peak <= SEARCH_CONCURRENCY


class TestClickMultiQuery:
    def _bootstrap_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIQUE_USER_ID", "u1")
        monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")
        monkeypatch.setenv("UNIQUE_API_KEY", "ukey_test")
        monkeypatch.setenv("UNIQUE_APP_ID", "app_test")

    @patch("unique_sdk.Search.create")
    def test_several_queries_in_one_call_exit_zero(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        result = CliRunner().invoke(cli_main, ["search", "revenue", "margin"])

        assert result.exit_code == 0
        assert mock_search.call_count == 2
        assert "=== query 2/2: 'margin' ===" in result.output

    @patch("unique_sdk.Search.create")
    def test_all_failing_exits_one(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(
            IDS_BY_QUERY, fail_queries=frozenset({"revenue", "margin"})
        )

        result = CliRunner().invoke(cli_main, ["search", "revenue", "margin"])

        assert result.exit_code == 1

    def test_no_query_is_a_usage_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._bootstrap_env(monkeypatch)

        result = CliRunner().invoke(cli_main, ["search"])

        assert result.exit_code == 2

    @patch("unique_sdk.cli.cli.cmd_search_many")
    @patch("unique_sdk.cli.cli.cmd_search")
    def test_single_query_does_not_use_the_multi_query_path(
        self,
        mock_single: MagicMock,
        mock_many: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_single.return_value = "Found 1 result(s):"

        CliRunner().invoke(cli_main, ["search", "revenue"])

        mock_single.assert_called_once()
        mock_many.assert_not_called()

    @patch("unique_sdk.Search.create")
    def test_single_query_output_has_no_query_header(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        result = CliRunner().invoke(cli_main, ["search", "margin"])

        assert result.exit_code == 0
        assert result.output.startswith("Found 1 result(s):\n\n<source1>")
