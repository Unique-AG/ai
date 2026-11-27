from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.crawlers.firecrawl.service import (
    FirecrawlCrawlerService,
    _resolve_batch_scrape_status_url,
)


class _FirecrawlSingleScrapeTransport:
    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/scrape"):
            if request.url.path.endswith("/batch/scrape"):
                return httpx.Response(404)
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "markdown": "# Firecrawl markdown",
                        "metadata": {"sourceURL": "https://example.com"},
                    },
                },
            )

        return httpx.Response(404)


class _FirecrawlBatchSequenceTransport:
    def __init__(self) -> None:
        self._polls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/batch/scrape"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "id": "job-123",
                    "url": "https://api.firecrawl.dev/v2/batch/scrape/job-123",
                },
            )

        if request.method == "GET" and "/batch/scrape/job-123" in str(request.url):
            self._polls += 1
            if self._polls < 2:
                return httpx.Response(200, json={"status": "scraping"})
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "data": [
                        {
                            "url": "https://example.com",
                            "markdown": "# First",
                        },
                        {
                            "url": "https://example.org",
                            "markdown": "# Second",
                        },
                    ],
                },
            )

        if request.method == "POST" and request.url.path.endswith("/scrape"):
            return httpx.Response(404)

        return httpx.Response(404)


@pytest.fixture(autouse=True)
def firecrawl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    from unique_search_proxy_client.web.settings.providers.firecrawl import (
        _get_firecrawl_crawl_credentials,
    )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.crawlers.firecrawl.service.credentials",
        _get_firecrawl_crawl_credentials(),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    transport = _FirecrawlSingleScrapeTransport()
    pool_transport = httpx.MockTransport(transport)

    from unique_search_proxy_client.web.core.client.service import HttpClientRegistry

    async def mock_create_registry() -> HttpClientRegistry:
        http_client = httpx.AsyncClient(transport=pool_transport)
        return HttpClientRegistry.fixed(http_client)

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_registry",
        mock_create_registry,
    )
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.mark.ai
def test_resolve_batch_scrape_status_url() -> None:
    batch_scrape_endpoint = "https://api.firecrawl.dev/v2/batch/scrape"
    assert (
        _resolve_batch_scrape_status_url(
            {"url": "https://api.firecrawl.dev/v2/batch/scrape/job-1"},
            batch_scrape_endpoint=batch_scrape_endpoint,
        )
        == "https://api.firecrawl.dev/v2/batch/scrape/job-1"
    )
    assert (
        _resolve_batch_scrape_status_url(
            {"id": "job-1"},
            batch_scrape_endpoint=batch_scrape_endpoint,
        )
        == "https://api.firecrawl.dev/v2/batch/scrape/job-1"
    )
    assert (
        _resolve_batch_scrape_status_url(
            {},
            batch_scrape_endpoint=batch_scrape_endpoint,
        )
        is None
    )


@pytest.mark.ai
def test_firecrawl_single_url_uses_scrape_endpoint() -> None:
    transport = _FirecrawlSingleScrapeTransport()

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.FIRECRAWL.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(transport)
        ) as http_client:
            service = FirecrawlCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert results[0].content == "# Firecrawl markdown"

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_firecrawl_multiple_urls_use_batch_scrape_and_poll() -> None:
    transport = _FirecrawlBatchSequenceTransport()

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com", "https://example.org"],
                "crawler": CrawlerType.FIRECRAWL.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(transport)
        ) as http_client:
            service = FirecrawlCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert transport._polls >= 2
        assert [result.content for result in results] == ["# First", "# Second"]

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_firecrawl_crawl_route(client: TestClient) -> None:
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com"],
            "crawler": CrawlerType.FIRECRAWL.value,
            "timeout": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["content"] == "# Firecrawl markdown"


@pytest.mark.ai
def test_firecrawl_maps_missing_markdown_on_scrape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/scrape"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"metadata": {"sourceURL": "https://example.com"}},
                },
            )
        return httpx.Response(404)

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.FIRECRAWL.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            service = FirecrawlCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert results[0].error is not None
        assert results[0].error.code == ProxyErrorCode.UPSTREAM_ERROR.value
        assert results[0].raw is not None

    import asyncio

    asyncio.run(run())


class _FirecrawlBatchOutOfOrderTransport:
    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/batch/scrape"):
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "id": "job-456",
                    "url": "https://api.firecrawl.dev/v2/batch/scrape/job-456",
                },
            )
        if request.method == "GET" and "/batch/scrape/job-456" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "data": [
                        {
                            "markdown": "# Report PDF",
                            "metadata": {
                                "sourceURL": "https://example.org/report.pdf",
                                "url": "https://cdn.example.org/report.pdf",
                            },
                        },
                        {
                            "markdown": "# Home",
                            "metadata": {"sourceURL": "https://example.com"},
                        },
                    ],
                },
            )
        return httpx.Response(404)


@pytest.mark.ai
def test_firecrawl_batch__maps_results_by_source_url__when_out_of_order() -> None:
    """
    Purpose: Match each batch scrape result to its URL by metadata.sourceURL.
    Why this matters: Firecrawl returns batch items in completion order, so matching by position gives the model one page's text under another page's URL.
    Setup summary: Two URLs; the batch answers them in reverse order with sourceURL in metadata.
    """
    request = parse_crawl_request(
        {
            "urls": ["https://example.com/", "https://example.org/report.pdf"],
            "crawler": CrawlerType.FIRECRAWL.value,
            "timeout": 30,
        },
    )

    async def run() -> list[str]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(_FirecrawlBatchOutOfOrderTransport())
        ) as http_client:
            service = FirecrawlCrawlerService(http_client=http_client)
            results = await service.crawl(request)
        return [result.content for result in results]

    assert asyncio.run(run()) == ["# Home", "# Report PDF"]


@pytest.mark.ai
def test_firecrawl_crawl__sends_zero_data_retention__from_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the deployment setting reaches the Firecrawl scrape call.
    Why this matters: The flag lives in the proxy settings, not in the request,
        so a missing hand-over would silently keep page content at Firecrawl.
    Setup summary: Turn the setting on, crawl one URL through a capturing
        transport; assert the body carries `zeroDataRetention: true`.
    """
    from unique_search_proxy_client.web.core.crawlers.firecrawl import service

    monkeypatch.setattr(
        service,
        "credentials",
        service.credentials.model_copy(update={"zero_data_retention": "zdr"}),
    )
    bodies: list[dict[str, object]] = []
    inner = _FirecrawlSingleScrapeTransport()

    def capture(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            bodies.append(json.loads(request.content))
        return inner(request)

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.FIRECRAWL.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(capture)
        ) as http_client:
            await FirecrawlCrawlerService(http_client=http_client).crawl(request)

    asyncio.run(run())

    assert bodies[0]["zeroDataRetention"] is True


@pytest.mark.ai
@pytest.mark.parametrize(
    "urls",
    [["https://example.com"], ["https://example.com", "https://example.org"]],
    ids=["single-scrape", "batch-scrape"],
)
def test_firecrawl_crawl__sends_zero_data_retention__from_the_request(
    monkeypatch: pytest.MonkeyPatch,
    urls: list[str],
) -> None:
    """
    Purpose: Verify a crawler configuration can turn zero data retention on for
        its own reads when the deployment runs without it.
    Why this matters: Single and multi-URL reads use different Firecrawl
        endpoints; a hand-over missing on one would keep page content at
        Firecrawl for that path only.
    Setup summary: Deploy with `none`, crawl one and two URLs with the request
        switch on; assert the first POST body carries `zeroDataRetention: true`.
    """
    from unique_search_proxy_client.web.core.crawlers.firecrawl import service

    monkeypatch.setattr(
        service,
        "credentials",
        service.credentials.model_copy(update={"zero_data_retention": "none"}),
    )
    bodies: list[dict[str, object]] = []
    inner = (
        _FirecrawlSingleScrapeTransport()
        if len(urls) == 1
        else _FirecrawlBatchSequenceTransport()
    )

    def capture(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            bodies.append(json.loads(request.content))
        return inner(request)

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": urls,
                "crawler": CrawlerType.FIRECRAWL.value,
                "timeout": 30,
                "zeroDataRetention": True,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(capture)
        ) as http_client:
            await FirecrawlCrawlerService(http_client=http_client).crawl(request)

    asyncio.run(run())

    assert bodies[0]["zeroDataRetention"] is True
