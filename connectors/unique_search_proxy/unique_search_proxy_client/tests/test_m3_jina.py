from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.crawlers.jina.service import JinaCrawlerService


def _jina_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    url = body["url"]
    return httpx.Response(
        200,
        json={
            "code": 200,
            "data": {"url": url, "content": f"# Jina content for {url}"},
        },
    )


@pytest.fixture(autouse=True)
def jina_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JINA_API_KEY", "test-key")
    from unique_search_proxy_client.web.settings.providers.jina import (
        _get_jina_crawl_credentials,
    )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.crawlers.jina.service.credentials",
        _get_jina_crawl_credentials(),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    pool_transport = httpx.MockTransport(_jina_handler)

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
def test_jina_service_returns_one_result_per_url() -> None:
    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://a.example", "https://b.example"],
                "crawler": CrawlerType.JINA.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(_jina_handler),
        ) as http_client:
            service = JinaCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert len(results) == 2
        assert results[0].content == "# Jina content for https://a.example"
        assert results[1].content == "# Jina content for https://b.example"

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_jina_crawl_route(client: TestClient) -> None:
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com"],
            "crawler": CrawlerType.JINA.value,
            "timeout": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["content"] == "# Jina content for https://example.com"


@pytest.mark.ai
def test_jina_maps_non_200_reader_code() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 422, "data": None})

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.JINA.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            service = JinaCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert results[0].error is not None
        assert results[0].error.code == ProxyErrorCode.UPSTREAM_ERROR.value
        assert results[0].raw == {"code": 422, "data": None}

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_jina_includes_upstream_message_and_raw_on_auth_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 401,
                "status": "error",
                "message": "Invalid Jina API key",
            },
        )

    async def run() -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.JINA.value,
                "timeout": 30,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            service = JinaCrawlerService(http_client=http_client)
            results = await service.crawl(request)

        assert results[0].error is not None
        assert (
            results[0].error.message == "Jina reader error (401): Invalid Jina API key"
        )
        assert results[0].raw == {
            "code": 401,
            "status": "error",
            "message": "Invalid Jina API key",
        }

    import asyncio

    asyncio.run(run())
