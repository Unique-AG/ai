"""Tests for ``unique-cli web-search search`` with several queries (UN-27454)."""

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
from unique_sdk.cli.commands.web_search import (
    MAX_SEARCH_QUERIES,
    SEARCH_CONCURRENCY,
    WEB_SEARCH_ERROR_PREFIX,
    cmd_web_search,
    cmd_web_search_many,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.state import ShellState


def _state() -> ShellState:
    return ShellState(
        Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
    )


@pytest.fixture(autouse=True)
def _isolate_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


class _FakeResource:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict_recursive(self) -> dict[str, Any]:
        return self._payload


def _payload(query: str, urls: list[str]) -> dict[str, Any]:
    return {
        "engine": "Google",
        "query": query,
        "object": "web-search.search",
        "results": [
            {"url": url, "title": f"T {url}", "snippet": f"S {url}", "content": ""}
            for url in urls
        ],
    }


def _search_by_query(
    urls_by_query: dict[str, list[str]],
    *,
    delay_by_query: dict[str, float] | None = None,
    fail_queries: frozenset[str] = frozenset(),
) -> Callable[..., _FakeResource]:
    delays = delay_by_query or {}

    def _search(**kwargs: Any) -> _FakeResource:
        query = kwargs["query"]
        time.sleep(delays.get(query, 0.0))
        if query in fail_queries:
            raise unique_sdk.APIError(f"upstream failed for {query}")
        return _FakeResource(_payload(query, urls_by_query[query]))

    return _search


def _manifest_rows(tmp_path: Path) -> list[dict[str, Any]]:
    manifest = tmp_path / ".unique" / "web-refs.jsonl"
    return [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


URLS = {
    "git": ["https://a.example/git", "https://shared.example/history"],
    "redis": ["https://b.example/redis", "https://shared.example/history"],
    "docker": ["https://c.example/docker"],
}


class TestMultiQueryOrderAndNumbering:
    @patch("unique_sdk.WebSearch.search")
    def test_results_follow_query_order_not_completion_order(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(
            URLS, delay_by_query={"git": 0.3, "redis": 0.1, "docker": 0.0}
        )

        out = cmd_web_search_many(_state(), ["git", "redis", "docker"])

        assert out.index("'git'") < out.index("'redis'") < out.index("'docker'")
        assert "[websource1]" in out.split("'redis'")[0]

    @patch("unique_sdk.WebSearch.search")
    def test_source_numbers_are_assigned_in_query_order(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(
            URLS, delay_by_query={"git": 0.3, "docker": 0.0}
        )

        cmd_web_search_many(_state(), ["git", "redis", "docker"], output_json=True)

        numbers = {row["url"]: row["sourceNumber"] for row in _manifest_rows(tmp_path)}
        assert numbers == {
            "https://a.example/git": 1,
            "https://shared.example/history": 2,
            "https://b.example/redis": 3,
            "https://c.example/docker": 4,
        }

    @patch("unique_sdk.WebSearch.search")
    def test_shared_url_keeps_one_number_and_one_row_per_search(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        def _search(**kwargs: Any) -> _FakeResource:
            payload = _payload(kwargs["query"], URLS[kwargs["query"]])
            for result in payload["results"]:
                result["snippet"] = f"snippet from {kwargs['query']}"
            return _FakeResource(payload)

        mock_search.side_effect = _search

        out = cmd_web_search_many(_state(), ["git", "redis"], output_json=True)

        parsed = json.loads(out)
        shared = [
            result["sourceNumber"]
            for block in parsed
            for result in block["results"]
            if result["url"] == "https://shared.example/history"
        ]
        assert shared == [2, 2]
        shared_rows = [
            row
            for row in _manifest_rows(tmp_path)
            if row["url"] == "https://shared.example/history"
        ]
        # One row per search that returned the URL, as separate calls write:
        # the reference keeps every snippet for the hallucination judge.
        assert [row["sourceNumber"] for row in shared_rows] == [2, 2]
        assert {row["snippet"] for row in shared_rows} == {
            "snippet from git",
            "snippet from redis",
        }

    @patch("unique_sdk.WebSearch.search")
    def test_block_header_does_not_repeat_the_query(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(URLS)

        out = cmd_web_search_many(_state(), ["git", "redis"])

        assert "=== query 1/2 ===" in out
        assert out.count("'git'") == 1

    @patch("unique_sdk.WebSearch.search")
    def test_numbering_is_identical_across_repeated_runs(
        self, mock_search: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        outputs: set[str] = set()
        delay_sets = [
            {"git": 0.2, "redis": 0.0, "docker": 0.1},
            {"git": 0.0, "redis": 0.2, "docker": 0.1},
            {"git": 0.1, "redis": 0.1, "docker": 0.0},
        ]
        for index, delays in enumerate(delay_sets):
            run_dir = tmp_path / f"run{index}"
            run_dir.mkdir()
            monkeypatch.chdir(run_dir)
            mock_search.side_effect = _search_by_query(URLS, delay_by_query=delays)
            outputs.add(
                cmd_web_search_many(
                    _state(), ["git", "redis", "docker"], output_json=True
                )
            )

        assert len(outputs) == 1

    @patch("unique_sdk.WebSearch.search")
    def test_manifest_is_valid_jsonl(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(URLS)

        cmd_web_search_many(_state(), ["git", "redis", "docker"])

        rows = _manifest_rows(tmp_path)
        assert [row["sourceNumber"] for row in rows] == [1, 2, 3, 2, 4]


class TestMultiQueryFailures:
    @patch("unique_sdk.WebSearch.search")
    def test_connection_error_in_one_query_keeps_the_others(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        def _search(**kwargs: Any) -> _FakeResource:
            if kwargs["query"] == "redis":
                raise unique_sdk.APIConnectionError("timed out")
            return _FakeResource(_payload(kwargs["query"], URLS[kwargs["query"]]))

        mock_search.side_effect = _search

        out = cmd_web_search_many(_state(), ["git", "redis", "docker"])

        assert not out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert "timed out" in out
        assert "https://a.example/git" in out
        assert "https://c.example/docker" in out
        assert "1 of 3 queries failed" in out

    @patch("unique_sdk.WebSearch.search")
    def test_failed_query_block_names_the_query(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(
            URLS, fail_queries=frozenset({"redis"})
        )

        out = cmd_web_search_many(_state(), ["git", "redis"])

        assert "query: 'redis'\nERROR:" in out

    @patch("unique_sdk.WebSearch.search")
    def test_failed_query_keeps_the_others(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(
            URLS, fail_queries=frozenset({"redis"})
        )

        out = cmd_web_search_many(_state(), ["git", "redis", "docker"])

        assert not out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert "upstream failed for redis" in out
        assert "https://a.example/git" in out
        assert "https://c.example/docker" in out
        assert "1 of 3 queries failed" in out

    @patch("unique_sdk.WebSearch.search")
    def test_failed_query_is_an_error_entry_in_json(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(
            URLS, fail_queries=frozenset({"redis"})
        )

        parsed = json.loads(
            cmd_web_search_many(_state(), ["git", "redis", "docker"], output_json=True)
        )

        assert [block["query"] for block in parsed] == ["git", "redis", "docker"]
        assert "upstream failed for redis" in parsed[1]["error"]
        assert "results" not in parsed[1]
        assert parsed[0]["results"][0]["sourceNumber"] == 1

    @pytest.mark.parametrize("output_json", [False, True])
    @patch("unique_sdk.WebSearch.search")
    def test_all_queries_failing_returns_an_error_output(
        self, mock_search: MagicMock, output_json: bool
    ) -> None:
        mock_search.side_effect = _search_by_query(
            URLS, fail_queries=frozenset({"git", "redis"})
        )

        out = cmd_web_search_many(_state(), ["git", "redis"], output_json=output_json)

        assert out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert "upstream failed for git" in out
        assert "upstream failed for redis" in out

    @patch("unique_sdk.WebSearch.search")
    def test_too_many_queries_is_rejected_before_any_request(
        self, mock_search: MagicMock
    ) -> None:
        queries = [f"q{i}" for i in range(MAX_SEARCH_QUERIES + 1)]

        out = cmd_web_search_many(_state(), queries)

        assert out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert str(MAX_SEARCH_QUERIES) in out
        mock_search.assert_not_called()

    @patch("unique_sdk.WebSearch.search")
    def test_invalid_engine_config_is_rejected_before_any_request(
        self, mock_search: MagicMock
    ) -> None:
        out = cmd_web_search_many(_state(), ["a", "b"], engine_config_raw="not-json")

        assert out.startswith(WEB_SEARCH_ERROR_PREFIX)
        mock_search.assert_not_called()


class TestMultiQueryConcurrency:
    @patch("unique_sdk.WebSearch.search")
    def test_requests_overlap_but_stay_within_the_bound(
        self, mock_search: MagicMock
    ) -> None:
        queries = [f"q{i}" for i in range(MAX_SEARCH_QUERIES)]
        urls = {query: [f"https://{query}.example"] for query in queries}
        in_flight = 0
        peak = 0
        lock = threading.Lock()
        inner = _search_by_query(urls, delay_by_query=dict.fromkeys(queries, 0.1))

        def _tracked(**kwargs: Any) -> _FakeResource:
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

        out = cmd_web_search_many(_state(), queries)

        assert not out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert 2 <= peak <= SEARCH_CONCURRENCY

    @patch("unique_sdk.WebSearch.search")
    def test_every_request_carries_the_shared_options(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.side_effect = _search_by_query(URLS)

        cmd_web_search_many(
            _state(),
            ["git", "redis"],
            fetch_size=3,
            include_content=True,
            engine_config_raw='{"searchEngineName":"Google"}',
            chat_id="chat_1",
        )

        calls = [call.kwargs for call in mock_search.call_args_list]
        assert sorted(call["query"] for call in calls) == ["git", "redis"]
        for call in calls:
            assert call["fetchSize"] == 3
            assert call["includeContent"] is True
            assert call["searchEngineConfig"] == {"searchEngineName": "Google"}
            assert call["chatId"] == "chat_1"
            assert call["user_id"] == "u1"
            assert call["company_id"] == "c1"


class TestConcurrentSingleQueryCalls:
    """Guards the manifest lock for callers that run separate processes at once."""

    @patch("unique_sdk.WebSearch.search")
    def test_parallel_single_calls_keep_the_manifest_consistent(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        mock_search.side_effect = _search_by_query(URLS)
        threads = [
            threading.Thread(target=cmd_web_search, args=(_state(), query))
            for query in URLS
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        rows = _manifest_rows(tmp_path)
        numbers_by_url: dict[str, set[int]] = {}
        for row in rows:
            numbers_by_url.setdefault(row["url"], set()).add(row["sourceNumber"])
        assert all(len(numbers) == 1 for numbers in numbers_by_url.values())
        distinct_numbers = [next(iter(n)) for n in numbers_by_url.values()]
        assert sorted(distinct_numbers) == [1, 2, 3, 4]


class TestClickMultiQuery:
    def _bootstrap_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIQUE_USER_ID", "u1")
        monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")
        monkeypatch.setenv("UNIQUE_API_KEY", "ukey_test")
        monkeypatch.setenv("UNIQUE_APP_ID", "app_test")

    @patch("unique_sdk.WebSearch.search")
    def test_several_queries_in_one_call_exit_zero(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(URLS)

        result = CliRunner().invoke(
            cli_main, ["web-search", "search", "git", "redis", "docker"]
        )

        assert result.exit_code == 0
        assert mock_search.call_count == 3
        assert result.output.index("'git'") < result.output.index("'docker'")

    @patch("unique_sdk.WebSearch.search")
    def test_partial_failure_exits_zero(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(
            URLS, fail_queries=frozenset({"redis"})
        )

        result = CliRunner().invoke(cli_main, ["web-search", "search", "git", "redis"])

        assert result.exit_code == 0
        assert "upstream failed for redis" in result.output

    @patch("unique_sdk.WebSearch.search")
    def test_all_failing_exits_one(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_by_query(
            URLS, fail_queries=frozenset({"git", "redis"})
        )

        result = CliRunner().invoke(
            cli_main, ["web-search", "search", "git", "redis", "--json"]
        )

        assert result.exit_code == 1

    def test_no_query_is_a_usage_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._bootstrap_env(monkeypatch)

        result = CliRunner().invoke(cli_main, ["web-search", "search"])

        assert result.exit_code == 2


class TestSingleQueryUnchanged:
    """UN-27454: one query keeps today's exact text and JSON shape."""

    def _bootstrap_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIQUE_USER_ID", "u1")
        monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")
        monkeypatch.setenv("UNIQUE_API_KEY", "ukey_test")
        monkeypatch.setenv("UNIQUE_APP_ID", "app_test")

    @patch("unique_sdk.WebSearch.search")
    def test_single_query_text_output_matches_the_golden_text(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.return_value = _FakeResource(_payload("q", ["https://a"]))

        result = CliRunner().invoke(cli_main, ["web-search", "search", "q"])

        assert result.exit_code == 0
        assert result.output == (
            "engine: Google    query: 'q'\n"
            "Found 1 result(s):\n"
            "\n"
            "  1. T https://a [websource1]\n"
            "     https://a\n"
            "     S https://a\n"
        )

    @patch("unique_sdk.WebSearch.search")
    def test_single_query_json_output_is_one_object_not_a_list(
        self, mock_search: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_search.return_value = _FakeResource(_payload("q", ["https://a"]))

        result = CliRunner().invoke(cli_main, ["web-search", "search", "q", "--json"])

        parsed = json.loads(result.output)
        assert list(parsed) == ["engine", "query", "results"]
        assert parsed["results"][0]["citation"] == "websource1"

    @patch("unique_sdk.cli.cli.cmd_web_search_many")
    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_single_query_does_not_use_the_multi_query_path(
        self,
        mock_single: MagicMock,
        mock_many: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_single.return_value = "Found 1 result(s):"

        CliRunner().invoke(cli_main, ["web-search", "search", "q"])

        mock_single.assert_called_once()
        mock_many.assert_not_called()
