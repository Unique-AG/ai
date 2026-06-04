from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerConfig
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.crawlers.basic.service import BasicCrawlerService

_HTML_PAGE = """
<html><head><title>Test</title></head>
<body><h1>Hello</h1><p>World</p></body></html>
"""


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "file.pdf" in url:
            return httpx.Response(
                200,
                text="%PDF-1.4",
                headers={"content-type": "application/pdf"},
            )
        if "blocked.example" in url:
            return httpx.Response(
                403,
                text="forbidden",
                headers={"content-type": "text/plain"},
            )
        if "example.com" in url:
            return httpx.Response(
                200,
                text=_HTML_PAGE,
                headers={"content-type": "text/html; charset=utf-8"},
            )
        return httpx.Response(404)

    pool_transport = httpx.MockTransport(handler)

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
def test_basic_crawler_service_returns_markdown() -> None:
    async def run() -> None:
        config = BasicCrawlerConfig(
            content_type_handlers={
                "text/html": ContentTypeHandlerPolicy.ALLOW,
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _req: httpx.Response(
                    200,
                    text=_HTML_PAGE,
                    headers={"content-type": "text/html"},
                ),
            ),
        ) as http_client:
            crawler = BasicCrawlerService(config, http_client=http_client)
            results = await crawler.crawl(
                ["https://example.com/article"],
                timeout=10,
            )

        assert len(results) == 1
        assert results[0].error is None
        assert results[0].content_type == "text/html"
        assert results[0].content is not None
        assert "Hello" in results[0].content
        assert results[0].raw is not None

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_crawl_endpoint_returns_per_url_results(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a", "https://blocked.example/x"],
            "config": {
                "crawler": "basic",
                "contentTypeHandlers": {"text/html": "allow"},
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["crawler"] == "basic"
    assert len(body["results"]) == 2

    success = next(r for r in body["results"] if "example.com/a" in r["url"])
    assert success["error"] is None
    assert success["contentType"] == "text/html"
    assert success["content"]
    assert success["raw"]

    failure = next(r for r in body["results"] if "blocked.example" in r["url"])
    assert failure["error"] is not None
    assert failure["error"]["code"] == ProxyErrorCode.UPSTREAM_ERROR.value
    assert failure["contentType"] == "text/plain"
    assert failure["raw"] == "forbidden"


@pytest.mark.ai
def test_crawl_returns_pdf_body_and_content_type(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/file.pdf"],
            "config": {"crawler": "basic"},
            "acceptedContentTypes": ["application/pdf"],
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is None
    assert result["contentType"] == "application/pdf"
    assert result["raw"] == "%PDF-1.4"
    assert result["content"] is None


@pytest.mark.ai
def test_crawl_reports_markdown_conversion_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_markdown(_html: str, *, timeout: float) -> str:
        raise ValueError("broken html")

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.crawlers.basic.processing.processors.html.html_to_markdown_async",
        fail_markdown,
    )

    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a"],
            "config": {
                "crawler": "basic",
                "contentTypeHandlers": {"text/html": "allow"},
            },
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is not None
    assert result["error"]["code"] == ProxyErrorCode.UPSTREAM_ERROR.value
    assert "processing failed" in result["error"]["message"].lower()
    assert result["raw"]
    assert result["content"] is None


@pytest.mark.ai
def test_crawl_without_processing_leaves_content_null(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a"],
            "config": {"crawler": "basic"},
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is None
    assert result["raw"]
    assert result["content"] is None


@pytest.mark.ai
def test_crawl_pdf_forbidden_skips_processing(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/file.pdf"],
            "config": {
                "crawler": "basic",
                "contentTypeHandlers": {"application/pdf": "forbid"},
            },
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is None
    assert result["raw"] == "%PDF-1.4"
    assert result["content"] is None


@pytest.mark.ai
def test_crawl_pdf_allowed_reports_processing_error(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/file.pdf"],
            "config": {
                "crawler": "basic",
                "contentTypeHandlers": {"application/pdf": "allow"},
            },
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is not None
    assert "PDF processing" in result["error"]["message"]
    assert result["raw"] == "%PDF-1.4"
