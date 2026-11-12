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
    MAX_SEARCH_CALLS_PER_TURN,
    MAX_SEARCH_CALLS_PER_TURN_ENV,
    MAX_SEARCH_QUERIES,
    MULTI_QUERY_TOKEN_BUDGET_ENV,
    SEARCH_CONCURRENCY,
    SEARCH_CONCURRENCY_ENV,
    SEARCH_ERROR_PREFIX,
    _estimated_tokens,
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


def _source_block(out: str, number: int) -> str:
    return out[out.index(f"<source{number}>") : out.index(f"</source{number}>")]


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

        assert out.index("=== query 1/3 ===\nquery: 'revenue'") < out.index(
            "=== query 2/3 ===\nquery: 'margin'"
        )
        assert out.index("=== query 2/3 ===\nquery: 'margin'") < out.index(
            "=== query 3/3 ===\nquery: 'headcount'"
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
            assert f"<|info|>{content_id}</|info|>" in _source_block(out, number)
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

        assert "=== query 1/2 ===\nquery: 'empty'\nNo results found." in out
        assert "<source1>" in out


class TestMultiQueryDeduplication:
    @patch("unique_sdk.Search.create")
    def test_a_chunk_found_twice_keeps_its_first_number(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(
            {"revenue": ["cont_a", "cont_b"], "growth": ["cont_b", "cont_c"]}
        )

        out = cmd_search_many(_state(), ["revenue", "growth"])

        assert out.count("<|info|>cont_b</|info|>") == 1
        assert "<|info|>cont_b</|info|>" in _source_block(out, 2)
        assert "<|info|>cont_c</|info|>" in _source_block(out, 3)
        assert "Also matched, shown in another block: [source2]" in out
        second_block = out.index("=== query 2/2 ===")
        assert out.index("<|info|>cont_b</|info|>") < second_block
        assert out.index("Also matched") > second_block
        assert _manifest_ids(tmp_path) == ["cont_a", "cont_b", "cont_c"]

    @patch("unique_sdk.Search.create")
    def test_other_chunks_of_the_same_document_stay_separate(
        self, mock_search: MagicMock
    ) -> None:
        def _search(**kwargs: Any) -> list[MagicMock]:
            result = _result("cont_a")
            result.chunkId = f"chunk_{kwargs['searchString']}"
            return [result]

        mock_search.side_effect = _search

        out = cmd_search_many(_state(), ["revenue", "growth"])

        assert "<source2>" in out
        assert "Also matched" not in out


class TestMultiQueryTokenBudget:
    @patch("unique_sdk.Search.create")
    def test_every_query_keeps_its_best_results_within_the_budget(
        self,
        mock_search: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        mock_search.side_effect = _search_by_query(
            {
                "revenue": ["cont_r1", "cont_r2", "cont_r3"],
                "margin": ["cont_m1", "cont_m2", "cont_m3"],
            }
        )
        budget = 3 * _estimated_tokens(_result("cont_r1"))
        monkeypatch.setenv(MULTI_QUERY_TOKEN_BUDGET_ENV, str(budget))

        out = cmd_search_many(_state(), ["revenue", "margin"])

        assert _manifest_ids(tmp_path) == ["cont_r1", "cont_r2", "cont_m1"]
        assert out.startswith(f"Output budget of about {budget} tokens reached: 3 ")
        assert "cont_r3" not in out
        assert "cont_m2" not in out

    @patch("unique_sdk.Search.create")
    def test_results_fit_without_a_budget_note(self, mock_search: MagicMock) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        out = cmd_search_many(_state(), ["revenue", "margin"])

        assert "Output budget" not in out
        assert out.startswith("=== query 1/2 ===")

    @patch("unique_sdk.Search.create")
    def test_invalid_budget_override_falls_back_to_the_default(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)
        monkeypatch.setenv(MULTI_QUERY_TOKEN_BUDGET_ENV, "lots")

        out = cmd_search_many(_state(), ["revenue", "margin"])

        assert "Output budget" not in out


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
        assert "=== query 2/3 ===\nquery: 'margin'\nERROR: search:" in out
        assert "upstream failed for margin" in out
        assert out.startswith("1 of 3 queries failed.")
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
        assert "=== query 1/2 ===\nquery: 'revenue'\nERROR: search:" in out
        assert "=== query 2/2 ===\nquery: 'margin'\nERROR: search:" in out

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


class TestMultiQueryManifest:
    @patch("unique_sdk.Search.create")
    def test_no_results_leave_the_manifest_untouched(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query({"a": [], "b": []})

        out = cmd_search_many(_state(), ["a", "b"])

        assert out.count("No results found.") == 2
        assert not (tmp_path / ".unique").exists()


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

    @patch("unique_sdk.Search.create")
    def test_concurrency_override_runs_queries_one_at_a_time(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(SEARCH_CONCURRENCY_ENV, "1")
        in_flight = 0
        peak = 0
        lock = threading.Lock()
        inner = _search_by_query(
            IDS_BY_QUERY, delay_by_query=dict.fromkeys(IDS_BY_QUERY, 0.05)
        )

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

        cmd_search_many(_state(), list(IDS_BY_QUERY))

        assert peak == 1


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

        result = CliRunner().invoke(cli_main, ["search", "revenue", "-q", "margin"])

        assert result.exit_code == 0
        assert mock_search.call_count == 2
        assert "=== query 2/2 ===\nquery: 'margin'" in result.output

    @patch("unique_sdk.Search.create")
    def test_unquoted_words_are_a_usage_error_not_several_searches(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)

        result = CliRunner().invoke(cli_main, ["search", "revenue", "growth", "2025"])

        assert result.exit_code == 2
        mock_search.assert_not_called()

    @patch("unique_sdk.Search.create")
    def test_all_failing_exits_one(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(
            IDS_BY_QUERY, fail_queries=frozenset({"revenue", "margin"})
        )

        result = CliRunner().invoke(cli_main, ["search", "revenue", "-q", "margin"])

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


class TestSearchCallCapPerTurn:
    @pytest.fixture(autouse=True)
    def _in_turn(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("UNIQUE_TURN_IDENTITY_FILE", raising=False)
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg_1")
        monkeypatch.setenv(MAX_SEARCH_CALLS_PER_TURN_ENV, "2")

    @patch("unique_sdk.Search.create")
    def test_a_turn_over_its_cap_is_refused_without_a_request(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        cmd_search(_state(), "margin")
        cmd_search(_state(), "margin")
        out = cmd_search(_state(), "margin")

        assert out.startswith(f"{SEARCH_ERROR_PREFIX} this turn reached its limit of 2")
        assert mock_search.call_count == 2

    @patch("unique_sdk.Search.create")
    def test_a_call_with_several_queries_counts_once(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)

        cmd_search_many(_state(), ["revenue", "margin", "headcount"])
        out = cmd_search_many(_state(), ["revenue", "margin"])

        assert "=== query 2/2 ===" in out
        assert mock_search.call_count == 5
        assert cmd_search(_state(), "margin").startswith(SEARCH_ERROR_PREFIX)

    @patch("unique_sdk.Search.create")
    def test_a_new_turn_starts_counting_again(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)
        cmd_search(_state(), "margin")
        cmd_search(_state(), "margin")

        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg_2")

        assert cmd_search(_state(), "margin").startswith("Found 1 result(s)")

    @patch("unique_sdk.Search.create")
    def test_the_cap_follows_the_turn_identity_file(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)
        identity = tmp_path / ".unique" / "turn.json"
        identity.parent.mkdir()
        monkeypatch.setenv("UNIQUE_TURN_IDENTITY_FILE", str(identity))
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg_stale")

        identity.write_text(json.dumps({"message_id": "msg_a"}), encoding="utf-8")
        cmd_search(_state(), "margin")
        cmd_search(_state(), "margin")
        refused = cmd_search(_state(), "margin")
        identity.write_text(json.dumps({"message_id": "msg_b"}), encoding="utf-8")

        assert refused.startswith(SEARCH_ERROR_PREFIX)
        assert cmd_search(_state(), "margin").startswith("Found 1 result(s)")

    @patch("unique_sdk.Search.create")
    def test_without_a_turn_there_is_no_cap(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)
        monkeypatch.delenv("UNIQUE_MESSAGE_ID")

        outputs = [cmd_search(_state(), "margin") for _ in range(3)]

        assert all(out.startswith("Found 1 result(s)") for out in outputs)

    @patch("unique_sdk.Search.create")
    def test_the_default_cap_is_one_hundred(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_search.side_effect = _search_by_query(IDS_BY_QUERY)
        monkeypatch.delenv(MAX_SEARCH_CALLS_PER_TURN_ENV)

        outputs = [cmd_search(_state(), "margin") for _ in range(101)]

        assert MAX_SEARCH_CALLS_PER_TURN == 100
        assert outputs[99].startswith("Found 1 result(s)")
        assert outputs[100].startswith(SEARCH_ERROR_PREFIX)
