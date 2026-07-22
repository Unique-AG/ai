"""Tests for the unique-cli web-search subcommands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

import unique_sdk
from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.web_search import (
    WEB_CRAWL_ERROR_PREFIX,
    WEB_SEARCH_ERROR_PREFIX,
    _annotate_web_results_for_citations,
    _format_crawl_results,
    _format_crawl_results_json,
    _format_search_results,
    _format_search_results_json,
    _parse_crawler_config,
    _parse_engine_config,
    _payload_from_resource,
    cmd_web_crawl,
    cmd_web_search,
    is_error_output,
)
from unique_sdk.cli.commands.web_search_config import (
    ENV_CONFIG_PATH,
    ConfigOverrides,
    WebSearchCLIConfigError,
    is_full_platform_config,
    load_overrides,
    parse_config_data,
    resolve_config_path,
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


def _state() -> ShellState:
    return ShellState(_config())


@pytest.fixture(autouse=True)
def _isolate_web_refs_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _make_search_payload(
    *,
    engine: str = "Google",
    query: str = "q",
    results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "engine": engine,
        "query": query,
        "results": results or [],
        "object": "web-search.search",
    }


def _make_crawl_payload(
    *,
    crawler: str = "BasicCrawler",
    results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "crawler": crawler,
        "results": results or [],
        "object": "web-search.crawl",
    }


class _FakeResource:
    """Stand-in for a UniqueObject — exposes ``to_dict_recursive``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict_recursive(self) -> dict[str, Any]:
        return self._payload


class TestParseConfigOverrides:
    def test_parse_engine_config_none(self) -> None:
        assert _parse_engine_config(None) is None

    def test_parse_engine_config_object(self) -> None:
        result = _parse_engine_config('{"searchEngineName": "Google"}')
        assert result == {"searchEngineName": "Google"}

    def test_parse_engine_config_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_engine_config("{bad}")

    def test_parse_engine_config_not_object(self) -> None:
        with pytest.raises(ValueError, match="must be a JSON object"):
            _parse_engine_config('["a"]')

    def test_parse_crawler_config_none(self) -> None:
        assert _parse_crawler_config(None) is None

    def test_parse_crawler_config_object(self) -> None:
        result = _parse_crawler_config('{"crawlerType": "BasicCrawler"}')
        assert result == {"crawlerType": "BasicCrawler"}

    def test_parse_crawler_config_not_object(self) -> None:
        with pytest.raises(ValueError, match="must be a JSON object"):
            _parse_crawler_config("123")


class TestPayloadExtraction:
    def test_to_dict_recursive_takes_precedence(self) -> None:
        payload = {"engine": "Google", "query": "x", "results": []}
        assert _payload_from_resource(_FakeResource(payload)) == payload

    def test_dict_passthrough(self) -> None:
        payload = {"engine": "Brave", "query": "y", "results": []}
        assert _payload_from_resource(payload) == payload

    def test_attribute_fallback(self) -> None:
        class Plain:
            engine = "Tavily"
            query = "z"
            results: list[dict[str, Any]] = []

        result = _payload_from_resource(Plain())
        assert result == {"engine": "Tavily", "query": "z", "results": []}


class TestSearchFormatting:
    def test_search_human_no_results(self) -> None:
        out = _format_search_results(_make_search_payload(results=[]))
        assert "No results found" in out
        assert "engine=Google" in out

    def test_search_human_with_results(self) -> None:
        out = _format_search_results(
            _make_search_payload(
                results=[
                    {
                        "url": "https://a.com",
                        "title": "A",
                        "snippet": "snippet a",
                        "content": "",
                    },
                    {
                        "url": "https://b.com",
                        "title": "B",
                        "snippet": "snippet b",
                        "content": "page text",
                    },
                ]
            )
        )
        assert "engine: Google" in out
        assert "1. A" in out
        assert "     https://a.com" in out
        assert "snippet a" in out
        assert "[9 chars of content]" in out

    def test_search_long_snippet_is_truncated(self) -> None:
        long = "x" * 300
        out = _format_search_results(
            _make_search_payload(
                results=[
                    {
                        "url": "https://a.com",
                        "title": "A",
                        "snippet": long,
                        "content": "",
                    }
                ]
            )
        )
        assert "..." in out
        assert long not in out

    def test_search_json_envelope(self) -> None:
        payload = _make_search_payload(
            results=[
                {
                    "url": "u",
                    "title": "t",
                    "snippet": "s",
                    "content": "",
                    "sourceNumber": 1,
                    "citation": "websource1",
                }
            ]
        )
        parsed = json.loads(_format_search_results_json(payload))
        assert parsed == {
            "engine": "Google",
            "query": "q",
            "results": [
                {
                    "url": "u",
                    "title": "t",
                    "snippet": "s",
                    "content": "",
                    "sourceNumber": 1,
                    "citation": "websource1",
                }
            ],
        }


class TestCrawlFormatting:
    def test_crawl_human_no_results(self) -> None:
        out = _format_crawl_results(_make_crawl_payload(results=[]))
        assert "No crawl results" in out
        assert "BasicCrawler" in out

    def test_crawl_human_with_results(self) -> None:
        out = _format_crawl_results(
            _make_crawl_payload(
                results=[
                    {"url": "https://a.com", "content": "page text", "error": None},
                    {"url": "https://b.com", "content": "", "error": "boom"},
                    {"url": "https://c.com", "content": "", "error": None},
                ]
            )
        )
        assert "crawler: BasicCrawler" in out
        assert "1. https://a.com" in out
        assert "[9 chars]" in out
        assert "ERROR: boom" in out
        assert "(empty)" in out

    def test_crawl_json_envelope(self) -> None:
        payload = _make_crawl_payload(
            results=[
                {
                    "url": "u",
                    "content": "c",
                    "error": None,
                    "sourceNumber": 1,
                    "citation": "websource1",
                }
            ]
        )
        parsed = json.loads(_format_crawl_results_json(payload))
        assert parsed == {
            "crawler": "BasicCrawler",
            "results": [
                {
                    "url": "u",
                    "content": "c",
                    "error": None,
                    "sourceNumber": 1,
                    "citation": "websource1",
                }
            ],
        }


class TestCitationManifest:
    def test_annotates_results_and_writes_manifest(self, tmp_path: Path) -> None:
        payload = _make_search_payload(
            results=[
                {
                    "url": "https://example.com/a",
                    "title": "A",
                    "snippet": "Snippet A",
                    "content": "",
                }
            ]
        )
        manifest = tmp_path / ".unique" / "web-refs.jsonl"

        annotated = _annotate_web_results_for_citations(payload, refs_log_path=manifest)

        assert annotated["results"][0]["sourceNumber"] == 1
        assert annotated["results"][0]["citation"] == "websource1"
        entries = [
            json.loads(line)
            for line in manifest.read_text(encoding="utf-8").splitlines()
        ]
        assert entries == [
            {
                "sourceNumber": 1,
                "url": "https://example.com/a",
                "title": "A",
                "snippet": "Snippet A",
                "content": "",
                "error": None,
            }
        ]

    def test_reuses_source_number_for_crawled_url(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".unique" / "web-refs.jsonl"
        _annotate_web_results_for_citations(
            _make_search_payload(
                results=[
                    {
                        "url": "https://example.com/a",
                        "title": "A",
                        "snippet": "Snippet A",
                        "content": "",
                    }
                ]
            ),
            refs_log_path=manifest,
        )

        annotated = _annotate_web_results_for_citations(
            _make_crawl_payload(
                results=[
                    {
                        "url": "https://example.com/a",
                        "content": "# Full page",
                        "error": None,
                    }
                ]
            ),
            refs_log_path=manifest,
        )

        assert annotated["results"][0]["sourceNumber"] == 1
        entries = [
            json.loads(line)
            for line in manifest.read_text(encoding="utf-8").splitlines()
        ]
        assert [entry["sourceNumber"] for entry in entries] == [1, 1]

    def test_source_numbering_continues_across_calls(self, tmp_path: Path) -> None:
        manifest = tmp_path / ".unique" / "web-refs.jsonl"
        _annotate_web_results_for_citations(
            _make_search_payload(
                results=[
                    {
                        "url": "https://example.com/a",
                        "title": "A",
                        "snippet": "Snippet A",
                        "content": "",
                    }
                ]
            ),
            refs_log_path=manifest,
        )

        annotated = _annotate_web_results_for_citations(
            _make_search_payload(
                results=[
                    {
                        "url": "https://example.com/b",
                        "title": "B",
                        "snippet": "Snippet B",
                        "content": "",
                    }
                ]
            ),
            refs_log_path=manifest,
        )

        assert annotated["results"][0]["sourceNumber"] == 2

    def test_null_results_are_treated_as_empty(self, tmp_path: Path) -> None:
        payload = _make_search_payload()
        payload["results"] = None

        annotated = _annotate_web_results_for_citations(
            payload,
            refs_log_path=tmp_path / ".unique" / "web-refs.jsonl",
        )

        assert annotated["results"] == []

    def test_non_dict_results_are_logged_and_dropped(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Bugbot A7: non-dict result entries must be visible in logs, not
        silently swallowed, so missing citations are diagnosable.
        """
        payload = _make_search_payload(
            results=[
                "not-a-dict",
                {"url": "https://a", "title": "A", "snippet": "s", "content": ""},
            ]
        )

        with caplog.at_level("WARNING", logger="unique_sdk.cli.commands.web_search"):
            annotated = _annotate_web_results_for_citations(
                payload,
                refs_log_path=tmp_path / ".unique" / "web-refs.jsonl",
            )

        annotated_urls = [r.get("url") for r in annotated["results"]]
        assert annotated_urls == ["https://a"]
        assert any(
            "skipping non-dict web result" in record.getMessage()
            for record in caplog.records
        )


class TestFormatterRowLabel:
    """Bugbot A6: the human formatter's row label must come from the
    citation key (``sourceNumber``) when present, so what the LLM reads in
    the table matches the ``[websourceN]`` marker it is told to emit.
    """

    def test_search_formatter_uses_source_number(self, tmp_path: Path) -> None:
        payload = _make_search_payload(
            results=[
                {"url": "https://a", "title": "A", "snippet": "", "content": ""},
                {"url": "https://b", "title": "B", "snippet": "", "content": ""},
            ]
        )
        annotated = _annotate_web_results_for_citations(
            payload,
            refs_log_path=tmp_path / ".unique" / "web-refs.jsonl",
        )
        annotated["results"][0]["sourceNumber"] = 7
        annotated["results"][0]["citation"] = "websource7"

        out = _format_search_results(annotated)

        assert "  7. A [websource7]" in out
        assert "  1. A" not in out

    def test_crawl_formatter_uses_source_number(self, tmp_path: Path) -> None:
        payload = _make_crawl_payload(
            results=[
                {"url": "https://a", "content": "hello", "error": None},
            ]
        )
        annotated = _annotate_web_results_for_citations(
            payload,
            refs_log_path=tmp_path / ".unique" / "web-refs.jsonl",
        )
        annotated["results"][0]["sourceNumber"] = 4
        annotated["results"][0]["citation"] = "websource4"

        out = _format_crawl_results(annotated)

        assert "  4. https://a [websource4]" in out
        assert "  1. https://a" not in out


class TestCmdWebSearch:
    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_happy_path(self, mock_search: MagicMock) -> None:
        mock_search.return_value = _FakeResource(
            _make_search_payload(
                results=[
                    {"url": "https://a", "title": "A", "snippet": "s", "content": ""}
                ]
            )
        )
        out = cmd_web_search(_state(), "tax reform")
        assert "Found 1 result" in out
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["query"] == "tax reform"
        assert call_kwargs["user_id"] == "u1"
        assert call_kwargs["company_id"] == "c1"

    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_passes_overrides(self, mock_search: MagicMock) -> None:
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))
        cmd_web_search(
            _state(),
            "x",
            fetch_size=5,
            include_content=True,
            engine_config_raw='{"searchEngineName":"Google"}',
            crawler_config_raw='{"crawlerType":"BasicCrawler"}',
        )
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["fetchSize"] == 5
        assert call_kwargs["includeContent"] is True
        assert call_kwargs["searchEngineConfig"] == {"searchEngineName": "Google"}
        assert call_kwargs["crawlerConfig"] == {"crawlerType": "BasicCrawler"}

    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_json_output(self, mock_search: MagicMock) -> None:
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))
        out = cmd_web_search(_state(), "x", output_json=True)
        parsed = json.loads(out)
        assert parsed["engine"] == "Google"
        assert parsed["results"] == []

    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_invalid_engine_config(self, mock_search: MagicMock) -> None:
        out = cmd_web_search(_state(), "x", engine_config_raw="not-json")
        assert "web-search:" in out
        mock_search.assert_not_called()

    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_api_error(self, mock_search: MagicMock) -> None:
        mock_search.side_effect = unique_sdk.APIError("upstream boom")
        out = cmd_web_search(_state(), "x")
        assert "web-search:" in out
        assert "upstream boom" in out

    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_with_chat_id_sends_chat_id(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))
        cmd_web_search(_state(), "x", chat_id="chat_123")
        assert mock_search.call_args[1]["chatId"] == "chat_123"

    @patch("unique_sdk.WebSearch.search")
    def test_cmd_web_search_without_chat_id_omits_chat_id(
        self, mock_search: MagicMock
    ) -> None:
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))
        cmd_web_search(_state(), "x")
        assert "chatId" not in mock_search.call_args[1]


class TestCmdWebCrawl:
    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_happy_path(self, mock_crawl: MagicMock) -> None:
        mock_crawl.return_value = _FakeResource(
            _make_crawl_payload(
                results=[{"url": "https://a", "content": "page", "error": None}]
            )
        )
        out = cmd_web_crawl(_state(), ["https://a"], parallel=2)
        assert "Crawled 1 URL" in out
        call_kwargs = mock_crawl.call_args[1]
        assert call_kwargs["urls"] == ["https://a"]
        assert call_kwargs["parallel"] == 2

    def test_cmd_web_crawl_no_urls(self) -> None:
        out = cmd_web_crawl(_state(), [])
        assert "no URLs provided" in out

    def test_cmd_web_crawl_invalid_parallel(self) -> None:
        out = cmd_web_crawl(_state(), ["https://a"], parallel=0)
        assert "--parallel must be >= 1" in out

    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_passes_crawler_override(self, mock_crawl: MagicMock) -> None:
        mock_crawl.return_value = _FakeResource(_make_crawl_payload(results=[]))
        cmd_web_crawl(
            _state(),
            ["https://a"],
            crawler_config_raw='{"crawlerType":"Crawl4AI"}',
        )
        assert mock_crawl.call_args[1]["crawlerConfig"] == {"crawlerType": "Crawl4AI"}

    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_invalid_crawler_config(self, mock_crawl: MagicMock) -> None:
        out = cmd_web_crawl(_state(), ["https://a"], crawler_config_raw="garbage")
        assert "web-crawl:" in out
        mock_crawl.assert_not_called()

    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_json_output(self, mock_crawl: MagicMock) -> None:
        mock_crawl.return_value = _FakeResource(
            _make_crawl_payload(results=[{"url": "u", "content": "c", "error": None}])
        )
        out = cmd_web_crawl(_state(), ["u"], output_json=True)
        parsed = json.loads(out)
        assert parsed["crawler"] == "BasicCrawler"
        assert parsed["results"] == [
            {
                "url": "u",
                "content": "c",
                "error": None,
                "sourceNumber": 1,
                "citation": "websource1",
            }
        ]

    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_api_error(self, mock_crawl: MagicMock) -> None:
        mock_crawl.side_effect = unique_sdk.APIError("nope")
        out = cmd_web_crawl(_state(), ["u"])
        assert "web-crawl:" in out
        assert "nope" in out

    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_with_chat_id_sends_chat_id(
        self, mock_crawl: MagicMock
    ) -> None:
        mock_crawl.return_value = _FakeResource(_make_crawl_payload(results=[]))
        cmd_web_crawl(_state(), ["https://a"], chat_id="chat_123")
        assert mock_crawl.call_args[1]["chatId"] == "chat_123"

    @patch("unique_sdk.WebCrawl.crawl")
    def test_cmd_web_crawl_without_chat_id_omits_chat_id(
        self, mock_crawl: MagicMock
    ) -> None:
        mock_crawl.return_value = _FakeResource(_make_crawl_payload(results=[]))
        cmd_web_crawl(_state(), ["https://a"])
        assert "chatId" not in mock_crawl.call_args[1]


class TestApiResourceContract:
    """Verify the SDK resource posts to the right URL with the right shape."""

    @patch("unique_sdk.api_resources._web_search.WebSearch._static_request")
    def test_web_search_search_url(self, mock_request: MagicMock) -> None:
        mock_request.return_value = _make_search_payload(results=[])
        unique_sdk.WebSearch.search(user_id="u", company_id="c", query="q")
        method, url, *_ = mock_request.call_args[0]
        assert method == "post"
        assert url == "/web-search-api/search"

    @patch("unique_sdk.api_resources._web_search.WebCrawl._static_request")
    def test_web_crawl_crawl_url(self, mock_request: MagicMock) -> None:
        mock_request.return_value = _make_crawl_payload(results=[])
        unique_sdk.WebCrawl.crawl(
            user_id="u",
            company_id="c",
            urls=["https://a"],
        )
        method, url, *_ = mock_request.call_args[0]
        assert method == "post"
        assert url == "/web-search-api/crawl"

    def test_object_names(self) -> None:
        assert unique_sdk.WebSearch.OBJECT_NAME == "web-search.search"
        assert unique_sdk.WebCrawl.OBJECT_NAME == "web-search.crawl"

    def test_object_classes_registered(self) -> None:
        from unique_sdk._object_classes import OBJECT_CLASSES

        assert OBJECT_CLASSES["web-search.search"] is unique_sdk.WebSearch
        assert OBJECT_CLASSES["web-search.crawl"] is unique_sdk.WebCrawl


class TestErrorOutputDetection:
    def test_search_error_prefix_recognised(self) -> None:
        assert is_error_output(f"{WEB_SEARCH_ERROR_PREFIX} boom") is True

    def test_crawl_error_prefix_recognised(self) -> None:
        assert is_error_output(f"{WEB_CRAWL_ERROR_PREFIX} boom") is True

    def test_normal_output_not_flagged(self) -> None:
        assert is_error_output("Found 1 result(s):") is False
        assert is_error_output("crawler: BasicCrawler") is False


class TestIsFullPlatformConfig:
    """Mirrors the upstream unique-websearch heuristics."""

    def test_simple_overrides_not_detected(self) -> None:
        data = {
            "search_engine_config": {"fetch_size": 50},
            "crawler_config": {"timeout": 15},
        }
        assert is_full_platform_config(data) is False

    def test_mode_key_camel(self) -> None:
        assert is_full_platform_config({"webSearchActiveMode": "v2"}) is True

    def test_mode_key_snake(self) -> None:
        assert is_full_platform_config({"web_search_active_mode": "v1"}) is True

    def test_engine_discriminator_snake(self) -> None:
        data = {
            "search_engine_config": {
                "search_engine_name": "google",
                "fetch_size": 50,
            }
        }
        assert is_full_platform_config(data) is True

    def test_engine_discriminator_camel(self) -> None:
        data = {"searchEngineConfig": {"searchEngineName": "Google"}}
        assert is_full_platform_config(data) is True

    def test_crawler_discriminator_camel(self) -> None:
        data = {"crawlerConfig": {"crawlerType": "BasicCrawler"}}
        assert is_full_platform_config(data) is True

    def test_empty_dict(self) -> None:
        assert is_full_platform_config({}) is False

    def test_unrelated_keys(self) -> None:
        assert is_full_platform_config({"foo": "bar"}) is False


class TestParseConfigData:
    def test_full_platform_camel_passes_through(self) -> None:
        data = {
            "webSearchActiveMode": "v2",
            "searchEngineConfig": {"searchEngineName": "Google", "fetchSize": 7},
            "crawlerConfig": {"crawlerType": "BasicCrawler"},
        }
        overrides = parse_config_data(data)
        assert overrides.engine_config == {
            "searchEngineName": "Google",
            "fetchSize": 7,
        }
        assert overrides.crawler_config == {"crawlerType": "BasicCrawler"}
        assert overrides.fetch_size is None

    def test_full_platform_snake_passes_through(self) -> None:
        data = {
            "search_engine_config": {
                "search_engine_name": "google",
                "fetch_size": 7,
            },
            "crawler_config": {"crawler_type": "BasicCrawler"},
        }
        overrides = parse_config_data(data)
        assert overrides.engine_config == {
            "search_engine_name": "google",
            "fetch_size": 7,
        }
        assert overrides.crawler_config == {"crawler_type": "BasicCrawler"}

    def test_simple_overrides_extracts_fetch_size_snake(self) -> None:
        overrides = parse_config_data({"search_engine_config": {"fetch_size": 25}})
        assert overrides.engine_config is None
        assert overrides.crawler_config is None
        assert overrides.fetch_size == 25

    def test_simple_overrides_extracts_fetch_size_camel(self) -> None:
        overrides = parse_config_data({"searchEngineConfig": {"fetchSize": 13}})
        assert overrides.fetch_size == 13

    def test_simple_overrides_no_fetch_size(self) -> None:
        overrides = parse_config_data({"search_engine_config": {"timeout": 30}})
        assert overrides.is_empty

    def test_simple_overrides_invalid_fetch_size_type(self) -> None:
        with pytest.raises(WebSearchCLIConfigError, match="must be an integer"):
            parse_config_data({"search_engine_config": {"fetch_size": "ten"}})

    def test_simple_overrides_invalid_fetch_size_bool_rejected(self) -> None:
        with pytest.raises(WebSearchCLIConfigError, match="must be an integer"):
            parse_config_data({"search_engine_config": {"fetch_size": True}})

    def test_simple_overrides_invalid_fetch_size_value(self) -> None:
        with pytest.raises(WebSearchCLIConfigError, match="must be >= 1"):
            parse_config_data({"search_engine_config": {"fetch_size": 0}})

    def test_empty_dict_yields_empty(self) -> None:
        overrides = parse_config_data({})
        assert overrides.is_empty


class TestResolveConfigPath:
    def test_explicit_path_used_when_exists(self, tmp_path: Path) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text("{}", encoding="utf-8")
        assert resolve_config_path(str(cfg)) == cfg

    def test_explicit_missing_raises(self, tmp_path: Path) -> None:
        with pytest.raises(WebSearchCLIConfigError, match="not found"):
            resolve_config_path(str(tmp_path / "nope.json"))

    def test_env_var_used_when_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cfg = tmp_path / "via-env.json"
        cfg.write_text("{}", encoding="utf-8")
        monkeypatch.setenv(ENV_CONFIG_PATH, str(cfg))
        assert resolve_config_path(None) == cfg

    def test_env_var_missing_path_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ENV_CONFIG_PATH, str(tmp_path / "missing.json"))
        with pytest.raises(WebSearchCLIConfigError, match=ENV_CONFIG_PATH):
            resolve_config_path(None)

    def test_default_path_returned_when_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(ENV_CONFIG_PATH, raising=False)
        default = tmp_path / ".unique-websearch.json"
        default.write_text("{}", encoding="utf-8")
        with patch(
            "unique_sdk.cli.commands.web_search_config.DEFAULT_CONFIG_PATH",
            default,
        ):
            assert resolve_config_path(None) == default

    def test_no_default_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(ENV_CONFIG_PATH, raising=False)
        with patch(
            "unique_sdk.cli.commands.web_search_config.DEFAULT_CONFIG_PATH",
            tmp_path / ".unique-websearch.json",
        ):
            assert resolve_config_path(None) is None

    def test_explicit_path_expands_tilde(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        cfg = tmp_path / "ws.json"
        cfg.write_text("{}", encoding="utf-8")
        assert resolve_config_path("~/ws.json") == cfg


class TestLoadOverrides:
    def test_returns_empty_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(ENV_CONFIG_PATH, raising=False)
        with patch(
            "unique_sdk.cli.commands.web_search_config.DEFAULT_CONFIG_PATH",
            tmp_path / ".unique-websearch.json",
        ):
            assert load_overrides(None) == ConfigOverrides()

    def test_loads_full_platform_config(self, tmp_path: Path) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps(
                {
                    "searchEngineConfig": {"searchEngineName": "Google"},
                    "crawlerConfig": {"crawlerType": "BasicCrawler"},
                }
            ),
            encoding="utf-8",
        )
        overrides = load_overrides(str(cfg))
        assert overrides.engine_config == {"searchEngineName": "Google"}
        assert overrides.crawler_config == {"crawlerType": "BasicCrawler"}

    def test_loads_simple_overrides(self, tmp_path: Path) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps({"search_engine_config": {"fetch_size": 42}}),
            encoding="utf-8",
        )
        overrides = load_overrides(str(cfg))
        assert overrides.fetch_size == 42
        assert overrides.engine_config is None

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        cfg = tmp_path / "bad.json"
        cfg.write_text("{not json", encoding="utf-8")
        with pytest.raises(WebSearchCLIConfigError, match="Invalid JSON"):
            load_overrides(str(cfg))

    def test_non_object_top_level_raises(self, tmp_path: Path) -> None:
        cfg = tmp_path / "list.json"
        cfg.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(WebSearchCLIConfigError, match="JSON object"):
            load_overrides(str(cfg))


class TestCmdWebSearchConfigMerging:
    """File overrides apply when no inline override is given; inline always wins."""

    @patch("unique_sdk.WebSearch.search")
    def test_file_engine_config_used_when_no_inline_override(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps(
                {"searchEngineConfig": {"searchEngineName": "Google", "fetchSize": 5}}
            ),
            encoding="utf-8",
        )
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))

        cmd_web_search(_state(), "q", config_path=str(cfg))

        params = mock_search.call_args[1]
        assert params["searchEngineConfig"] == {
            "searchEngineName": "Google",
            "fetchSize": 5,
        }

    @patch("unique_sdk.WebSearch.search")
    def test_inline_engine_config_overrides_file(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps({"searchEngineConfig": {"searchEngineName": "Google"}}),
            encoding="utf-8",
        )
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))

        cmd_web_search(
            _state(),
            "q",
            engine_config_raw='{"searchEngineName":"Brave"}',
            config_path=str(cfg),
        )

        assert mock_search.call_args[1]["searchEngineConfig"] == {
            "searchEngineName": "Brave"
        }

    @patch("unique_sdk.WebSearch.search")
    def test_file_crawler_config_used_when_no_inline_override(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps(
                {
                    "searchEngineConfig": {"searchEngineName": "Google"},
                    "crawlerConfig": {"crawlerType": "BasicCrawler"},
                }
            ),
            encoding="utf-8",
        )
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))

        cmd_web_search(_state(), "q", config_path=str(cfg))

        assert mock_search.call_args[1]["crawlerConfig"] == {
            "crawlerType": "BasicCrawler"
        }

    @patch("unique_sdk.WebSearch.search")
    def test_simple_override_fetch_size_used_when_no_inline(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps({"search_engine_config": {"fetch_size": 42}}),
            encoding="utf-8",
        )
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))

        cmd_web_search(_state(), "q", config_path=str(cfg))

        params = mock_search.call_args[1]
        assert params["fetchSize"] == 42
        assert "searchEngineConfig" not in params

    @patch("unique_sdk.WebSearch.search")
    def test_inline_fetch_size_wins_over_file(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps({"search_engine_config": {"fetch_size": 42}}),
            encoding="utf-8",
        )
        mock_search.return_value = _FakeResource(_make_search_payload(results=[]))

        cmd_web_search(_state(), "q", fetch_size=3, config_path=str(cfg))

        assert mock_search.call_args[1]["fetchSize"] == 3

    @patch("unique_sdk.WebSearch.search")
    def test_invalid_config_file_returns_error(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "broken.json"
        cfg.write_text("{not json", encoding="utf-8")

        out = cmd_web_search(_state(), "q", config_path=str(cfg))

        assert out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert "Invalid JSON" in out
        mock_search.assert_not_called()

    @patch("unique_sdk.WebSearch.search")
    def test_missing_config_file_returns_error(
        self, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        out = cmd_web_search(_state(), "q", config_path=str(tmp_path / "missing.json"))
        assert out.startswith(WEB_SEARCH_ERROR_PREFIX)
        assert "not found" in out
        mock_search.assert_not_called()


class TestCmdWebCrawlConfigMerging:
    @patch("unique_sdk.WebCrawl.crawl")
    def test_file_crawler_config_used_when_no_inline_override(
        self, mock_crawl: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps({"crawlerConfig": {"crawlerType": "BasicCrawler"}}),
            encoding="utf-8",
        )
        mock_crawl.return_value = _FakeResource(_make_crawl_payload(results=[]))

        cmd_web_crawl(_state(), ["https://a"], config_path=str(cfg))

        assert mock_crawl.call_args[1]["crawlerConfig"] == {
            "crawlerType": "BasicCrawler"
        }

    @patch("unique_sdk.WebCrawl.crawl")
    def test_inline_crawler_config_overrides_file(
        self, mock_crawl: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "ws.json"
        cfg.write_text(
            json.dumps({"crawlerConfig": {"crawlerType": "BasicCrawler"}}),
            encoding="utf-8",
        )
        mock_crawl.return_value = _FakeResource(_make_crawl_payload(results=[]))

        cmd_web_crawl(
            _state(),
            ["https://a"],
            crawler_config_raw='{"crawlerType":"Crawl4AI"}',
            config_path=str(cfg),
        )

        assert mock_crawl.call_args[1]["crawlerConfig"] == {"crawlerType": "Crawl4AI"}

    @patch("unique_sdk.WebCrawl.crawl")
    def test_invalid_config_file_returns_error(
        self, mock_crawl: MagicMock, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "broken.json"
        cfg.write_text("{not json", encoding="utf-8")

        out = cmd_web_crawl(_state(), ["https://a"], config_path=str(cfg))

        assert out.startswith(WEB_CRAWL_ERROR_PREFIX)
        assert "Invalid JSON" in out
        mock_crawl.assert_not_called()


class TestClickIntegration:
    """End-to-end Click checks: --config plumbing, --version, exit codes."""

    def _bootstrap_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # LazyState.load_config requires user/company env vars.
        monkeypatch.setenv("UNIQUE_USER_ID", "u1")
        monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")
        monkeypatch.setenv("UNIQUE_API_KEY", "ukey_test")
        monkeypatch.setenv("UNIQUE_APP_ID", "app_test")
        monkeypatch.delenv(ENV_CONFIG_PATH, raising=False)

    def test_group_version_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._bootstrap_env(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "--version"])
        assert result.exit_code == 0
        assert "unique-cli web-search" in result.output

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_search_success_exit_zero(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_cmd.return_value = "Found 1 result(s):\n..."
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "search", "x"])
        assert result.exit_code == 0
        assert "Found 1 result(s)" in result.output

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_search_error_exit_one(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_cmd.return_value = f"{WEB_SEARCH_ERROR_PREFIX} something failed"
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "search", "x"])
        assert result.exit_code == 1
        assert "something failed" in result.output

    @patch("unique_sdk.cli.cli.cmd_web_crawl")
    def test_crawl_error_exit_one(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        mock_cmd.return_value = f"{WEB_CRAWL_ERROR_PREFIX} no URLs"
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "crawl"])
        assert result.exit_code == 1
        assert "no URLs" in result.output

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_group_config_flag_propagates_to_search(
        self,
        mock_cmd: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        self._bootstrap_env(monkeypatch)
        cfg = tmp_path / "ws.json"
        cfg.write_text("{}", encoding="utf-8")
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(
            cli_main, ["web-search", "--config", str(cfg), "search", "x"]
        )
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["config_path"] == str(cfg)

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_subcommand_config_overrides_group(
        self,
        mock_cmd: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        self._bootstrap_env(monkeypatch)
        group_cfg = tmp_path / "group.json"
        group_cfg.write_text("{}", encoding="utf-8")
        sub_cfg = tmp_path / "sub.json"
        sub_cfg.write_text("{}", encoding="utf-8")
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(
            cli_main,
            [
                "web-search",
                "--config",
                str(group_cfg),
                "search",
                "--config",
                str(sub_cfg),
                "x",
            ],
        )
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["config_path"] == str(sub_cfg)

    @patch("unique_sdk.cli.cli.cmd_web_crawl")
    def test_crawl_subcommand_config_passed_through(
        self,
        mock_cmd: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        self._bootstrap_env(monkeypatch)
        cfg = tmp_path / "ws.json"
        cfg.write_text("{}", encoding="utf-8")
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(
            cli_main,
            [
                "web-search",
                "crawl",
                "--config",
                str(cfg),
                "https://a",
            ],
        )
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["config_path"] == str(cfg)


class TestClickIntegrationChatId:
    """--chat-id / $UNIQUE_CHAT_ID resolution for web-search search/crawl."""

    def _bootstrap_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIQUE_USER_ID", "u1")
        monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")
        monkeypatch.setenv("UNIQUE_API_KEY", "ukey_test")
        monkeypatch.setenv("UNIQUE_APP_ID", "app_test")
        monkeypatch.delenv(ENV_CONFIG_PATH, raising=False)

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_search_reads_chat_id_from_env(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_from_env")
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "search", "x"])
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["chat_id"] == "chat_from_env"

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_search_chat_id_defaults_to_none_without_env(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        monkeypatch.delenv("UNIQUE_CHAT_ID", raising=False)
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "search", "x"])
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["chat_id"] is None

    @patch("unique_sdk.cli.cli.cmd_web_search")
    def test_search_explicit_flag_overrides_env(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_from_env")
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(
            cli_main, ["web-search", "search", "x", "--chat-id", "chat_explicit"]
        )
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["chat_id"] == "chat_explicit"

    @patch("unique_sdk.cli.cli.cmd_web_crawl")
    def test_crawl_reads_chat_id_from_env(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_from_env")
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "crawl", "https://a"])
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["chat_id"] == "chat_from_env"

    @patch("unique_sdk.cli.cli.cmd_web_crawl")
    def test_crawl_chat_id_defaults_to_none_without_env(
        self, mock_cmd: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._bootstrap_env(monkeypatch)
        monkeypatch.delenv("UNIQUE_CHAT_ID", raising=False)
        mock_cmd.return_value = "ok"
        runner = CliRunner()
        result = runner.invoke(cli_main, ["web-search", "crawl", "https://a"])
        assert result.exit_code == 0
        assert mock_cmd.call_args[1]["chat_id"] is None
