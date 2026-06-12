from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.crawlers.tavily.service import (
    TavilyCrawlerService,
)


def _extract_handler(request: httpx.Request) -> httpx.Response:
    import json

    body = json.loads(request.content.decode())
    urls = body.get("urls", [])
    return httpx.Response(
        200,
        json={
            "results": [
                {"url": url, "raw_content": f"# Content for {url}"} for url in urls
            ],
            "failed_results": [],
        },
    )


@pytest.fixture(autouse=True)
def tavily_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    from unique_search_proxy_client.web.settings.providers.tavily import (
        _get_tavily_crawl_credentials,
    )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.crawlers.tavily.service.credentials",
        _get_tavily_crawl_credentials(),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    pool_transport = httpx.MockTransport(_extract_handler)

    from unique_search_proxy_client.web.core.client.service import HttpClientPool

    async def mock_create_pool() -> HttpClientPool:
        http_client = httpx.AsyncClient(transport=pool_transport)
        return HttpClientPool(client=http_client)

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_pool",
        mock_create_pool,
    )
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.mark.ai
def test_tavily_service_batches_urls() -> None:
    calls: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content.decode())
        calls.append(body["urls"])
        return httpx.Response(
            200,
            json={
                "results": [
                    {"url": url, "raw_content": f"markdown-{url}"}
                    for url in body["urls"]
                ],
                "failed_results": [],
            },
        )

    async def run() -> None:
        urls = [f"https://example.com/{index}" for index in range(21)]
        request = parse_crawl_request(
            {
                "urls": urls,
                "crawler": CrawlerType.TAVILY.value,
                "extractDepth": "basic",
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            service = TavilyCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert len(calls) == 2
        assert len(calls[0]) == 20
        assert len(calls[1]) == 1
        assert len(results) == 21
        assert results[0].content == "markdown-https://example.com/0"

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_tavily_crawl_route(client: TestClient) -> None:
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com"],
            "crawler": CrawlerType.TAVILY.value,
            "extractDepth": "advanced",
            "timeout": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["crawler"] == CrawlerType.TAVILY.value
    assert body["results"][0]["content"] == "# Content for https://example.com"


@pytest.mark.ai
def test_tavily_maps_failed_results() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [],
                "failed_results": [
                    {"url": "https://bad.example", "error": "blocked"},
                ],
            },
        )

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://bad.example"],
                "crawler": CrawlerType.TAVILY.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            service = TavilyCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert results[0].error is not None
        assert results[0].error.code == ProxyErrorCode.UPSTREAM_ERROR.value
        assert results[0].error.message == "blocked"

    import asyncio

    asyncio.run(run())
