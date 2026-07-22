from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.schema import ProxyErrorCode
from unique_search_proxy_core.url_safety import ResolvedCrawlTarget

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.crawlers.basic.service import (
    BasicCrawlerService,
)
from unique_search_proxy_client.web.core.crawlers.pinned_egress import (
    PinnedEgressCrawler,
)
from unique_search_proxy_client.web.core.url_safety.gate import AllowedCrawlTarget

_HTML_PAGE = """
<html><head><title>Test</title></head>
<body><h1>Hello</h1><p>World</p></body></html>
"""


def _is_example_com_request(request: httpx.Request) -> bool:
    host_header = request.headers.get("host", "")
    if isinstance(host_header, bytes):
        host_header = host_header.decode()
    host_from_header = host_header.split(":", 1)[0]
    return request.url.host == "example.com" or host_from_header == "example.com"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        host_header = request.headers.get("host", "")
        if isinstance(host_header, bytes):
            host_header = host_header.decode()
        if "file.pdf" in url:
            return httpx.Response(
                200,
                text="%PDF-1.4",
                headers={"content-type": "application/pdf"},
            )
        if "blocked.example" in host_header or "blocked.example" in url:
            return httpx.Response(
                403,
                text="forbidden",
                headers={"content-type": "text/plain"},
            )
        if _is_example_com_request(request):
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
        request = parse_crawl_request(
            {
                "urls": ["https://example.com/article"],
                "crawler": CrawlerType.BASIC.value,
                "timeout": 10,
                "contentTypes": {"html": True},
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
            crawler = BasicCrawlerService(http_client=http_client)
            results = await crawler.crawl(request)

        assert len(results) == 1
        assert results[0].error is None
        assert results[0].content_type == "text/html"
        assert results[0].content is not None
        assert "Hello" in results[0].content
        assert results[0].raw is not None

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
def test_basic_crawler_service_implements_pinned_egress_protocol() -> None:
    crawler = BasicCrawlerService()
    assert isinstance(crawler, PinnedEgressCrawler)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__fetches_resolved_ip_with_host_and_sni() -> None:
    html = "<html><body><p>Hello</p></body></html>"
    response = httpx.Response(
        200,
        text=html,
        headers={"content-type": "text/html; charset=utf-8"},
        request=httpx.Request("GET", "https://93.184.216.34/docs?q=1"),
    )
    http_client = AsyncMock(spec=httpx.AsyncClient)
    http_client.get.return_value = response

    request = parse_crawl_request(
        {
            "urls": ["https://example.com/docs?q=1"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )
    allowed_targets = [
        AllowedCrawlTarget(
            display_url="https://example.com/docs?q=1",
            resolved=ResolvedCrawlTarget(
                normalized_url="https://example.com/docs?q=1",
                hostname="example.com",
                resolved_ip="93.184.216.34",
                used_dns_resolution=True,
            ),
        ),
    ]

    crawler = BasicCrawlerService(http_client=http_client)
    results = await crawler.crawl_pinned(request, allowed_targets)

    assert len(results) == 1
    assert results[0].error is None
    assert results[0].url == "https://example.com/docs?q=1"
    http_client.get.assert_called_once()
    assert http_client.get.call_args.args[0] == "https://93.184.216.34/docs?q=1"
    call_headers = http_client.get.call_args.kwargs["headers"]
    assert call_headers["Host"] == "example.com"
    assert call_headers["User-Agent"]
    assert (
        http_client.get.call_args.kwargs["extensions"]["sni_hostname"] == "example.com"
    )


@pytest.mark.ai
def test_crawl_endpoint_returns_per_url_results(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a", "https://blocked.example/x"],
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": {"html": True},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["crawler"] == CrawlerType.BASIC.value
    assert len(body["results"]) == 2

    success = next(r for r in body["results"] if "example.com/a" in r["url"])
    assert success["error"] is None
    assert success["contentType"] == "text/html"
    assert success["content"]
    assert success["raw"]

    failure = next(r for r in body["results"] if "blocked.example" in r["url"])
    assert failure["error"] is not None
    assert failure["error"]["code"] == ProxyErrorCode.UPSTREAM_ERROR.value
    assert failure["error"]["statusCode"] == 403
    assert failure["contentType"] == "text/plain"
    assert failure["raw"] == "forbidden"


@pytest.mark.ai
def test_crawl_records_per_url_outcome_metrics(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a", "https://blocked.example/x"],
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": {"html": True},
        },
    )
    assert resp.status_code == 200

    metrics = client.get("/metrics").text
    assert (
        'unique_search_proxy_crawl_url_outcomes_total{crawler="Basic",'
        'error_code="",http_status="",outcome="success"}' in metrics
    )
    assert (
        'unique_search_proxy_crawl_url_outcomes_total{crawler="Basic",'
        f'error_code="{ProxyErrorCode.UPSTREAM_ERROR.value}",'
        'http_status="403",outcome="error"}' in metrics
    )


@pytest.mark.ai
def test_crawl_returns_pdf_body_and_content_type(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/file.pdf"],
            "crawler": CrawlerType.BASIC.value,
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
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": {"html": True},
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
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": {
                "html": False,
                "xhtml": False,
                "plainText": False,
                "markdown": False,
                "pdf": False,
            },
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
            "crawler": CrawlerType.BASIC.value,
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
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": {"pdf": True},
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is not None
    assert "PDF processing" in result["error"]["message"]
    assert result["raw"] == "%PDF-1.4"
