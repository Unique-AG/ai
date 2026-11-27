import asyncio
import logging
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.url_safety import ResolvedCrawlTarget

import unique_web_search.services.crawlers.base as crawler_base_module
from unique_web_search.services.crawlers.basic import BasicCrawler
from unique_web_search.services.crawlers.registry import CRAWLER_REGISTRY
from unique_web_search.services.httpx_logging import hide_httpx_request_logs
from unique_web_search.services.search_engine.base import SearchEngine
from unique_web_search.services.search_engine.schema import WebSearchResult


@pytest.mark.ai
async def test_hide_httpx_request_logs__drops_request_lines__only_inside_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify httpx request lines are dropped inside the scope, including from tasks it starts.
    Why this matters: The lines carry full request URLs, but httpx logs elsewhere in the process must stay.
    Setup summary: Log request lines inside the scope, from a gathered task, and after the scope ends.
    """
    httpx_logger = logging.getLogger("httpx")

    async def log_request(label: str) -> None:
        httpx_logger.info("HTTP Request: GET https://example.com/?q=%s", label)

    with caplog.at_level(logging.INFO, logger="httpx"):
        with hide_httpx_request_logs():
            await log_request("hidden")
            await asyncio.gather(log_request("hidden-task"))
        await log_request("kept")

    assert "hidden" not in caplog.text
    assert "q=kept" in caplog.text


@pytest.mark.ai
async def test_search_and_crawl__hide_httpx_request_lines__from_legacy_calls(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify SearchEngine.search() and BaseCrawler.crawl() run provider calls inside the hiding scope.
    Why this matters: Dropping the scope from either entry point puts queries and crawled URLs back into httpx logs.
    Setup summary: Stub the legacy search and crawl to log an httpx request line; assert both ran and neither line is captured.
    """
    logged_urls: list[str] = []

    def log_request(url: str) -> None:
        logged_urls.append(url)
        logging.getLogger("httpx").info('HTTP Request: GET %s "HTTP/1.1 200 OK"', url)

    class StubConfig(BaseModel):
        pass

    class StubSearchEngine(SearchEngine[StubConfig]):
        async def _legacy_search(
            self, query: str, params: ExposedParams | None
        ) -> list[WebSearchResult]:
            log_request(f"https://search.example/?q={query}")
            return []

    async def legacy_crawl(_targets: list[ResolvedCrawlTarget]) -> list[str]:
        log_request("https://crawl.example/page")
        return []

    monkeypatch.setattr(crawler_base_module, "search_proxy_client_enabled", False)
    monkeypatch.setattr(
        crawler_base_module.UrlSafetyService,
        "validate_batch_urls",
        AsyncMock(return_value=[]),
    )
    crawler = BasicCrawler(
        CRAWLER_REGISTRY[CrawlerType.BASIC].config_cls(crawler=CrawlerType.BASIC)
    )
    monkeypatch.setattr(crawler, "_legacy_crawl", legacy_crawl)

    with caplog.at_level(logging.INFO, logger="httpx"):
        await StubSearchEngine(StubConfig()).search("query")
        await crawler.crawl(["https://crawl.example/page"])

    assert len(logged_urls) == 2
    assert "search.example" not in caplog.text
    assert "crawl.example" not in caplog.text
