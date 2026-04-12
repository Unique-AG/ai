"""Tests for the unique-websearch CLI (search + crawl subcommands)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from unique_web_search.cli.cli import main
from unique_web_search.cli.cli_config import (
    CLIConfigError,
    _is_full_platform_config,
    _nested_has_discriminator,
)
from unique_web_search.cli.commands.crawl import cmd_crawl
from unique_web_search.cli.commands.search import cmd_search
from unique_web_search.cli.formatting import (
    format_crawl_results,
    format_crawl_results_json,
    format_search_results,
    format_search_results_json,
)
from unique_web_search.services.search_engine.schema import WebSearchResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_result(i: int) -> WebSearchResult:
    return WebSearchResult(
        url=f"https://example.com/page{i}",
        title=f"Page {i} Title",
        snippet=f"Snippet for page {i}",
    )


# ---------------------------------------------------------------------------
# formatting — search
# ---------------------------------------------------------------------------


class TestFormatSearchResults:
    def test_empty(self) -> None:
        assert format_search_results([]) == "No results found."

    def test_basic_output(self) -> None:
        results = [_make_result(1), _make_result(2)]
        text = format_search_results(results)
        assert "Found 2 result(s):" in text
        assert "Page 1 Title" in text
        assert "https://example.com/page1" in text
        assert "Snippet for page 1" in text
        assert "Page 2 Title" in text

    def test_long_snippet_truncated(self) -> None:
        r = WebSearchResult(
            url="https://example.com",
            title="Title",
            snippet="x" * 300,
        )
        text = format_search_results([r])
        assert "..." in text
        assert len(text.split("\n")[3].strip()) <= 200 + 3

    def test_empty_snippet(self) -> None:
        r = WebSearchResult(url="https://example.com", title="Title", snippet="")
        text = format_search_results([r])
        assert "Title" in text
        assert "https://example.com" in text


class TestFormatSearchResultsJson:
    def test_roundtrips(self) -> None:
        results = [_make_result(1)]
        parsed = json.loads(format_search_results_json(results))
        assert len(parsed) == 1
        assert parsed[0]["url"] == "https://example.com/page1"
        assert parsed[0]["title"] == "Page 1 Title"
        assert parsed[0]["snippet"] == "Snippet for page 1"

    def test_empty(self) -> None:
        assert json.loads(format_search_results_json([])) == []


# ---------------------------------------------------------------------------
# formatting — crawl
# ---------------------------------------------------------------------------


class TestFormatCrawlResults:
    def test_empty(self) -> None:
        assert format_crawl_results([]) == "No crawl results."

    def test_success(self) -> None:
        results = [("https://example.com", "Some markdown content here", None)]
        text = format_crawl_results(results)
        assert "Crawled 1 URL(s):" in text
        assert "https://example.com" in text
        assert "[26 chars]" in text

    def test_error(self) -> None:
        results = [("https://example.com", "", "Connection timeout")]
        text = format_crawl_results(results)
        assert "ERROR: Connection timeout" in text

    def test_empty_content(self) -> None:
        results = [("https://example.com", "", None)]
        text = format_crawl_results(results)
        assert "(empty)" in text


class TestFormatCrawlResultsJson:
    def test_structure(self) -> None:
        results = [
            ("https://a.com", "content", None),
            ("https://b.com", "", "error msg"),
        ]
        parsed = json.loads(format_crawl_results_json(results))
        assert len(parsed) == 2
        assert parsed[0]["url"] == "https://a.com"
        assert parsed[0]["content"] == "content"
        assert parsed[0]["error"] is None
        assert parsed[1]["error"] == "error msg"


# ---------------------------------------------------------------------------
# cli_config — _is_full_platform_config
# ---------------------------------------------------------------------------


class TestIsFullPlatformConfig:
    def test_simple_overrides_not_detected(self) -> None:
        data = {
            "search_engine_config": {"fetch_size": 50},
            "crawler_config": {"timeout": 15},
        }
        assert _is_full_platform_config(data) is False

    def test_mode_key_detected(self) -> None:
        data = {"webSearchActiveMode": "v2"}
        assert _is_full_platform_config(data) is True

    def test_snake_mode_key_detected(self) -> None:
        data = {"web_search_active_mode": "v1"}
        assert _is_full_platform_config(data) is True

    def test_engine_discriminator_detected(self) -> None:
        data = {
            "search_engine_config": {
                "search_engine_name": "google",
                "fetch_size": 50,
            }
        }
        assert _is_full_platform_config(data) is True

    def test_crawler_discriminator_detected(self) -> None:
        data = {
            "crawler_config": {
                "crawler_type": "BasicCrawler",
                "timeout": 10,
            }
        }
        assert _is_full_platform_config(data) is True

    def test_empty_dict_not_detected(self) -> None:
        assert _is_full_platform_config({}) is False

    def test_unrelated_keys_not_detected(self) -> None:
        data = {"foo": "bar", "baz": 42}
        assert _is_full_platform_config(data) is False


class TestNestedHasDiscriminator:
    def test_found(self) -> None:
        data = {"nested": {"disc_key": "value"}}
        assert (
            _nested_has_discriminator(data, ("nested",), frozenset({"disc_key"}))
            is True
        )

    def test_not_found(self) -> None:
        data = {"nested": {"other": "value"}}
        assert (
            _nested_has_discriminator(data, ("nested",), frozenset({"disc_key"}))
            is False
        )

    def test_not_a_dict(self) -> None:
        data = {"nested": "scalar"}
        assert (
            _nested_has_discriminator(data, ("nested",), frozenset({"disc_key"}))
            is False
        )

    def test_missing_key(self) -> None:
        data = {}
        assert (
            _nested_has_discriminator(data, ("nested",), frozenset({"disc_key"}))
            is False
        )


# ---------------------------------------------------------------------------
# commands/search — cmd_search
# ---------------------------------------------------------------------------


class TestCmdSearch:
    @patch("unique_web_search.cli.commands.search._instantiate_engine")
    @patch("unique_web_search.cli.commands.search.asyncio.run")
    def test_search_text(self, mock_run: MagicMock, mock_engine: MagicMock) -> None:
        results = [_make_result(1)]
        mock_run.return_value = results

        engine = MagicMock()
        mock_engine.return_value = engine

        config = MagicMock()
        output = cmd_search(config, "test query")
        assert "Found 1 result(s):" in output
        assert "Page 1 Title" in output

    @patch("unique_web_search.cli.commands.search._instantiate_engine")
    @patch("unique_web_search.cli.commands.search.asyncio.run")
    def test_search_json(self, mock_run: MagicMock, mock_engine: MagicMock) -> None:
        results = [_make_result(1)]
        mock_run.return_value = results
        mock_engine.return_value = MagicMock()

        config = MagicMock()
        output = cmd_search(config, "test", output_json=True)
        parsed = json.loads(output)
        assert len(parsed) == 1

    @patch("unique_web_search.cli.commands.search._instantiate_engine")
    @patch("unique_web_search.cli.commands.search.asyncio.run")
    def test_no_results(self, mock_run: MagicMock, mock_engine: MagicMock) -> None:
        mock_run.return_value = []
        mock_engine.return_value = MagicMock()

        assert cmd_search(MagicMock(), "q") == "No results found."

    @patch("unique_web_search.cli.commands.search._instantiate_engine")
    @patch("unique_web_search.cli.commands.search.asyncio.run")
    def test_no_results_json(self, mock_run: MagicMock, mock_engine: MagicMock) -> None:
        mock_run.return_value = []
        mock_engine.return_value = MagicMock()

        assert cmd_search(MagicMock(), "q", output_json=True) == "[]"

    @patch("unique_web_search.cli.commands.search._instantiate_engine")
    @patch("unique_web_search.cli.commands.search.asyncio.run")
    def test_fetch_size_override(
        self, mock_run: MagicMock, mock_engine: MagicMock
    ) -> None:
        mock_run.return_value = []
        mock_engine.return_value = MagicMock()

        config = MagicMock()
        cmd_search(config, "q", fetch_size=5)
        assert config.fetch_size == 5


# ---------------------------------------------------------------------------
# commands/crawl — cmd_crawl
# ---------------------------------------------------------------------------


class TestCmdCrawl:
    @patch("unique_web_search.cli.commands.crawl.get_crawler_service")
    def test_crawl_text(self, mock_get: MagicMock) -> None:
        crawler = MagicMock()
        crawler.crawl = AsyncMock(return_value=["# Page 1 content"])
        mock_get.return_value = crawler

        output = cmd_crawl(MagicMock(), ["https://example.com"], parallel=10)
        assert "Crawled 1 URL(s):" in output
        assert "https://example.com" in output

    @patch("unique_web_search.cli.commands.crawl.get_crawler_service")
    def test_crawl_json(self, mock_get: MagicMock) -> None:
        crawler = MagicMock()
        crawler.crawl = AsyncMock(return_value=["content"])
        mock_get.return_value = crawler

        output = cmd_crawl(
            MagicMock(), ["https://example.com"], parallel=10, output_json=True
        )
        parsed = json.loads(output)
        assert len(parsed) == 1
        assert parsed[0]["content"] == "content"
        assert parsed[0]["error"] is None

    @patch("unique_web_search.cli.commands.crawl.get_crawler_service")
    def test_crawl_batch_error(self, mock_get: MagicMock) -> None:
        crawler = MagicMock()
        crawler.crawl = AsyncMock(side_effect=RuntimeError("network fail"))
        mock_get.return_value = crawler

        output = cmd_crawl(MagicMock(), ["https://a.com", "https://b.com"], parallel=10)
        assert "network fail" in output

    @patch("unique_web_search.cli.commands.crawl.get_crawler_service")
    def test_parallel_batching(self, mock_get: MagicMock) -> None:
        crawler = MagicMock()
        call_count = 0

        async def mock_crawl(urls: list[str]) -> list[str]:
            nonlocal call_count
            call_count += 1
            return [f"content-{i}" for i in range(len(urls))]

        crawler.crawl = mock_crawl
        mock_get.return_value = crawler

        urls = [f"https://example.com/{i}" for i in range(5)]
        output = cmd_crawl(MagicMock(), urls, parallel=2, output_json=True)
        parsed = json.loads(output)
        assert len(parsed) == 5
        assert call_count == 3  # batches of 2, 2, 1


# ---------------------------------------------------------------------------
# CLI Click integration
# ---------------------------------------------------------------------------


class TestClickSearch:
    @patch("unique_web_search.cli.cli.load_search_engine_config")
    @patch("unique_web_search.cli.cli.cmd_search")
    def test_search_success(self, mock_cmd: MagicMock, mock_cfg: MagicMock) -> None:
        mock_cmd.return_value = "Found 1 result(s):\n..."
        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query"])
        assert result.exit_code == 0
        assert "Found 1 result(s)" in result.output

    @patch("unique_web_search.cli.cli.load_search_engine_config")
    def test_search_config_error(self, mock_cfg: MagicMock) -> None:
        mock_cfg.side_effect = CLIConfigError("no engine")
        runner = CliRunner()
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 1
        assert "no engine" in result.output

    @patch("unique_web_search.cli.cli.load_search_engine_config")
    @patch("unique_web_search.cli.cli.cmd_search")
    def test_search_runtime_error(
        self, mock_cmd: MagicMock, mock_cfg: MagicMock
    ) -> None:
        mock_cmd.side_effect = ValueError("API failure")
        runner = CliRunner()
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 1
        assert "API failure" in result.output

    @patch("unique_web_search.cli.cli.load_search_engine_config")
    @patch("unique_web_search.cli.cli.cmd_search")
    def test_search_json_flag(self, mock_cmd: MagicMock, mock_cfg: MagicMock) -> None:
        mock_cmd.return_value = "[]"
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--json", "test"])
        assert result.exit_code == 0
        mock_cmd.assert_called_once()
        _, kwargs = mock_cmd.call_args
        assert kwargs["output_json"] is True


class TestClickCrawl:
    @patch("unique_web_search.cli.cli.load_crawler_config")
    @patch("unique_web_search.cli.cli.cmd_crawl")
    def test_crawl_success(self, mock_cmd: MagicMock, mock_cfg: MagicMock) -> None:
        mock_cmd.return_value = "Crawled 1 URL(s):\n..."
        runner = CliRunner()
        result = runner.invoke(main, ["crawl", "https://example.com"])
        assert result.exit_code == 0
        assert "Crawled" in result.output

    def test_crawl_no_urls(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["crawl"])
        assert result.exit_code == 1
        assert "no URLs" in result.output

    @patch("unique_web_search.cli.cli.load_crawler_config")
    @patch("unique_web_search.cli.cli.cmd_crawl")
    def test_crawl_stdin(self, mock_cmd: MagicMock, mock_cfg: MagicMock) -> None:
        mock_cmd.return_value = "Crawled 2 URL(s):\n..."
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["crawl", "--stdin"],
            input="https://a.com\nhttps://b.com\n",
        )
        assert result.exit_code == 0
        _, kwargs = mock_cmd.call_args
        assert "https://a.com" in kwargs["urls"]
        assert "https://b.com" in kwargs["urls"]

    @patch("unique_web_search.cli.cli.load_crawler_config")
    @patch("unique_web_search.cli.cli.cmd_crawl")
    def test_crawl_parallel_option(
        self, mock_cmd: MagicMock, mock_cfg: MagicMock
    ) -> None:
        mock_cmd.return_value = "Crawled 1 URL(s):\n..."
        runner = CliRunner()
        result = runner.invoke(main, ["crawl", "--parallel", "5", "https://a.com"])
        assert result.exit_code == 0
        _, kwargs = mock_cmd.call_args
        assert kwargs["parallel"] == 5

    @patch("unique_web_search.cli.cli.load_crawler_config")
    def test_crawl_config_error(self, mock_cfg: MagicMock) -> None:
        mock_cfg.side_effect = CLIConfigError("no crawler")
        runner = CliRunner()
        result = runner.invoke(main, ["crawl", "https://a.com"])
        assert result.exit_code == 1
        assert "no crawler" in result.output

    @patch("unique_web_search.cli.cli.load_crawler_config")
    @patch("unique_web_search.cli.cli.cmd_crawl")
    def test_crawl_runtime_error(
        self, mock_cmd: MagicMock, mock_cfg: MagicMock
    ) -> None:
        mock_cmd.side_effect = RuntimeError("crawl failed")
        runner = CliRunner()
        result = runner.invoke(main, ["crawl", "https://a.com"])
        assert result.exit_code == 1
        assert "crawl failed" in result.output


class TestClickMain:
    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Two-phase" in result.output
        assert "search" in result.output
        assert "crawl" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "unique-websearch" in result.output
