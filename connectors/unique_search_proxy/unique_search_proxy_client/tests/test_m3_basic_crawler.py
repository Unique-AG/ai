from __future__ import annotations

import gzip
import logging
from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.schema import ProxyErrorCode
from unique_search_proxy_core.url_safety import (
    ResolvedCrawlTarget,
    bypass_crawl_target,
)

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
        assert results[0].raw is None

    import asyncio

    asyncio.run(run())


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__returns_raw_body__when_include_raw() -> None:
    """
    Purpose: Verify includeRaw returns the upstream body next to the markdown.
    Why this matters: Debugging and benchmarks need the body the proxy saw,
        while normal requests leave it out to keep responses small.
    Setup summary: HTML page crawled with includeRaw; assert content and raw.
    """
    http_client, _ = _recording_client(
        lambda _: httpx.Response(
            200,
            text=_HTML_PAGE,
            headers={"content-type": "text/html"},
        ),
    )
    request = parse_crawl_request(
        {
            "urls": ["https://example.com/article"],
            "crawler": CrawlerType.BASIC.value,
            "includeRaw": True,
        },
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        (result,) = await crawler.crawl_pinned(
            request,
            [_pinned_target("https://example.com/article", "example.com")],
        )

    assert result.error is None
    assert result.content is not None
    assert "Hello" in result.content
    assert result.raw == _HTML_PAGE


@pytest.mark.ai
def test_basic_crawler_service_implements_pinned_egress_protocol() -> None:
    crawler = BasicCrawlerService()
    assert isinstance(crawler, PinnedEgressCrawler)


def _recording_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[httpx.AsyncClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return httpx.AsyncClient(transport=httpx.MockTransport(record)), requests


def _pinned_target(url: str, hostname: str) -> AllowedCrawlTarget:
    return AllowedCrawlTarget(
        display_url=url,
        resolved=ResolvedCrawlTarget(
            normalized_url=url,
            hostname=hostname,
            resolved_ip="93.184.216.34",
            used_dns_resolution=True,
        ),
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__fetches_resolved_ip_with_host_and_sni() -> None:
    http_client, requests = _recording_client(
        lambda _: httpx.Response(
            200,
            text="<html><body><p>Hello</p></body></html>",
            headers={"content-type": "text/html; charset=utf-8"},
        ),
    )
    request = parse_crawl_request(
        {
            "urls": ["https://example.com/docs?q=1"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(
            request,
            [_pinned_target("https://example.com/docs?q=1", "example.com")],
        )

    assert len(results) == 1
    assert results[0].error is None
    assert results[0].url == "https://example.com/docs?q=1"
    assert len(requests) == 1
    assert str(requests[0].url) == "https://93.184.216.34/docs?q=1"
    assert requests[0].headers["Host"] == "example.com"
    assert requests[0].headers["User-Agent"]
    assert requests[0].headers["Accept-Encoding"] == "gzip, deflate"
    assert requests[0].extensions["sni_hostname"] == "example.com"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__blocks_private_redirect_from_real_get() -> None:
    http_client, requests = _recording_client(
        lambda _: httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"}),
    )
    request = parse_crawl_request(
        {
            "urls": ["https://example.com/start"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(
            request,
            [_pinned_target("https://example.com/start", "example.com")],
        )

    assert len(results) == 1
    assert results[0].error is not None
    assert results[0].error.code == ProxyErrorCode.FORBIDDEN_TARGET.value
    assert len(requests) == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__isolates_malformed_redirect_to_affected_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["Host"] == "malformed.example":
            return httpx.Response(302, headers={"Location": "http://[::1"})
        return httpx.Response(
            200,
            text="valid content",
            headers={"content-type": "text/plain"},
        )

    http_client, _ = _recording_client(handler)
    request = parse_crawl_request(
        {
            "urls": [
                "https://malformed.example/start",
                "https://valid.example/start",
            ],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
        },
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(
            request,
            [
                _pinned_target("https://malformed.example/start", "malformed.example"),
                _pinned_target("https://valid.example/start", "valid.example"),
            ],
        )

    malformed_result, valid_result = results
    assert malformed_result.error is not None
    assert malformed_result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value
    assert valid_result.error is None
    assert valid_result.content == "valid content"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__delegates_private_redirect_to_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import unique_search_proxy_client.web.core.crawlers.basic.service as service_module

    monkeypatch.setattr(
        service_module,
        "url_safety_settings",
        service_module.url_safety_settings.model_copy(update={"enabled": False}),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(
                302,
                headers={"Location": "http://127.0.0.1/internal"},
            )
        return httpx.Response(
            200,
            text="internal content",
            headers={"content-type": "text/plain"},
        )

    http_client, requests = _recording_client(handler)
    request = parse_crawl_request(
        {
            "urls": ["https://public.example.com/start"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
        },
    )
    allowed_targets = [
        AllowedCrawlTarget(
            display_url="https://public.example.com/start",
            resolved=bypass_crawl_target("https://public.example.com/start"),
        ),
    ]

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(request, allowed_targets)

    assert len(results) == 1
    assert results[0].error is None
    assert results[0].content == "internal content"
    assert len(requests) == 2
    assert str(requests[1].url) == "http://127.0.0.1/internal"
    assert "sni_hostname" not in requests[1].extensions
    assert requests[1].headers["Host"] == "127.0.0.1"


@pytest.mark.ai
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (httpx.ReadTimeout("timed out"), ProxyErrorCode.UPSTREAM_TIMEOUT.value),
        (httpx.ConnectError("refused"), ProxyErrorCode.UPSTREAM_ERROR.value),
    ],
)
async def test_crawl_pinned__maps_transport_errors_to_upstream_errors(
    error: httpx.HTTPError,
    expected_code: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        logging.getLogger("unique_search_proxy_client"), "propagate", True
    )

    def raise_error(_request: httpx.Request) -> httpx.Response:
        raise error

    http_client, _ = _recording_client(raise_error)
    request = parse_crawl_request(
        {
            "urls": ["https://example.com/start"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
        },
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(
            request,
            [_pinned_target("https://example.com/start", "example.com")],
        )

    assert results[0].error is not None
    assert results[0].error.code == expected_code
    assert "Basic crawl" in caplog.text
    assert "example.com" not in caplog.text


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__reports_processing_timeout(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import unique_search_proxy_client.web.core.crawlers.basic.service as service_module

    monkeypatch.setattr(
        logging.getLogger("unique_search_proxy_client"), "propagate", True
    )

    async def time_out(*_args: object, **_kwargs: object) -> str:
        raise service_module.ContentProcessingTimeoutError("too slow")

    monkeypatch.setattr(service_module, "process_content", time_out)
    http_client, _ = _recording_client(
        lambda _: httpx.Response(
            200,
            text=_HTML_PAGE,
            headers={"content-type": "text/html"},
        ),
    )
    request = parse_crawl_request(
        {
            "urls": ["https://example.com/start"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(
            request,
            [_pinned_target("https://example.com/start", "example.com")],
        )

    assert results[0].error is not None
    assert results[0].error.code == ProxyErrorCode.UPSTREAM_TIMEOUT.value
    assert results[0].raw is None
    assert "Basic crawl processing timed out" in caplog.text
    assert "example.com" not in caplog.text


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
    assert success["raw"] is None

    failure = next(r for r in body["results"] if "blocked.example" in r["url"])
    assert failure["error"] is not None
    assert failure["error"]["code"] == ProxyErrorCode.UPSTREAM_ERROR.value
    assert failure["error"]["statusCode"] == 403
    assert failure["contentType"] == "text/plain"
    assert failure["raw"] is None


@pytest.mark.ai
def test_crawl_endpoint_returns_raw_bodies__when_include_raw(
    client: TestClient,
) -> None:
    """
    Purpose: Verify includeRaw returns upstream bodies for successes and HTTP errors.
    Why this matters: This is the debugging path once raw is off by default.
    Setup summary: One HTML URL and one 403 URL with includeRaw; assert both
        results carry the upstream body.
    """
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a", "https://blocked.example/x"],
            "crawler": CrawlerType.BASIC.value,
            "includeRaw": True,
        },
    )
    assert resp.status_code == 200
    success, failure = resp.json()["results"]
    assert success["error"] is None
    assert success["content"]
    assert success["raw"] == _HTML_PAGE
    assert failure["error"]["statusCode"] == 403
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
def test_crawl_rejects_pdf__when_pdf_processing_disabled(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/file.pdf"],
            "crawler": CrawlerType.BASIC.value,
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"]["code"] == ProxyErrorCode.UNSUPPORTED_CONTENT_TYPE.value
    assert "application/pdf" in result["error"]["message"]
    assert result["contentType"] == "application/pdf"
    assert result["raw"] is None
    assert result["content"] is None


@pytest.mark.ai
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("headers", "expected_content_type"),
    [
        ({"content-type": "application/pdf"}, "application/pdf"),
        ({"content-type": "image/png"}, "image/png"),
        ({}, None),
    ],
)
async def test_crawl_pinned__skips_body__for_unprocessed_content_type(
    headers: dict[str, str],
    expected_content_type: str | None,
) -> None:
    """
    Purpose: Verify pages of unprocessed types are rejected from their headers alone.
    Why this matters: Downloading a body the proxy would discard costs memory
        and budget for nothing; binary bodies also inflate when decoded as text.
    Setup summary: One URL streams a body with an unprocessed (or missing)
        content type, another serves HTML; assert only the first errors, its
        body is never read, and the HTML page still succeeds.
    """
    skipped_body_read: list[bool] = []

    async def skipped_body() -> AsyncIterator[bytes]:
        skipped_body_read.append(True)
        yield b"%PDF-1.4"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["Host"] == "binary.example":
            return httpx.Response(200, headers=headers, content=skipped_body())
        return httpx.Response(
            200, text=_HTML_PAGE, headers={"content-type": "text/html"}
        )

    http_client, _ = _recording_client(handler)

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        skipped_result, html_result = await crawler.crawl_pinned(
            _plain_crawl_request(
                "https://binary.example/file", "https://html.example/page"
            ),
            [
                _pinned_target("https://binary.example/file", "binary.example"),
                _pinned_target("https://html.example/page", "html.example"),
            ],
        )

    assert skipped_result.error is not None
    assert skipped_result.error.code == ProxyErrorCode.UNSUPPORTED_CONTENT_TYPE.value
    assert skipped_result.content_type == expected_content_type
    assert skipped_body_read == []
    assert html_result.error is None
    assert html_result.content is not None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__skips_error_body__unless_include_raw() -> None:
    """
    Purpose: Verify HTTP error responses are reported without reading their body.
    Why this matters: Error pages are only useful for debugging, which
        includeRaw covers.
    Setup summary: 500 response with a streaming body; assert the status code
        is reported and the body is never read.
    """
    error_body_read: list[bool] = []

    async def error_body() -> AsyncIterator[bytes]:
        error_body_read.append(True)
        yield b"<html>Internal Server Error</html>"

    http_client, _ = _recording_client(
        lambda _: httpx.Response(
            500, headers={"content-type": "text/html"}, content=error_body()
        ),
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        (result,) = await crawler.crawl_pinned(
            _plain_crawl_request("https://error.example/page"),
            [_pinned_target("https://error.example/page", "error.example")],
        )

    assert result.error is not None
    assert result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value
    assert result.error.status_code == 500
    assert result.raw is None
    assert error_body_read == []


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
    assert result["raw"] is None
    assert result["content"] is None


_ALL_PROCESSING_DISABLED = {
    "html": False,
    "xhtml": False,
    "plainText": False,
    "markdown": False,
    "pdf": False,
}


@pytest.mark.ai
def test_crawl_without_processing_rejects_page(client: TestClient) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a"],
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": _ALL_PROCESSING_DISABLED,
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"]["code"] == ProxyErrorCode.UNSUPPORTED_CONTENT_TYPE.value
    assert result["contentType"] == "text/html"
    assert result["raw"] is None
    assert result["content"] is None


@pytest.mark.ai
def test_crawl_without_processing_returns_raw_body__when_include_raw(
    client: TestClient,
) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/a"],
            "crawler": CrawlerType.BASIC.value,
            "contentTypes": _ALL_PROCESSING_DISABLED,
            "includeRaw": True,
        },
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["error"] is None
    assert result["raw"] == _HTML_PAGE
    assert result["content"] is None


@pytest.mark.ai
def test_crawl_pdf_forbidden_returns_raw_body__when_include_raw(
    client: TestClient,
) -> None:
    resp = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/file.pdf"],
            "crawler": CrawlerType.BASIC.value,
            "includeRaw": True,
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
    assert result["raw"] is None


def _cap_crawler_bodies(monkeypatch: pytest.MonkeyPatch, *, max_kib: int) -> None:
    import unique_search_proxy_client.web.core.crawlers.basic.service as service_module

    monkeypatch.setattr(
        service_module,
        "http_client_settings",
        service_module.http_client_settings.model_copy(
            update={"max_response_kib": max_kib},
        ),
    )


def _plain_crawl_request(*urls: str) -> BaseModel:
    return parse_crawl_request(
        {
            "urls": list(urls),
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
        },
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__maps_oversized_body_to_per_url_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify one oversized URL fails alone with RESPONSE_TOO_LARGE.
    Why this matters: A single huge page must not fail the whole batch.
    Setup summary: 1 KiB cap; one 4 KiB body and one small body; assert the
        large URL errors and the small one succeeds.
    """
    _cap_crawler_bodies(monkeypatch, max_kib=1)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["Host"] == "big.example":
            return httpx.Response(200, text="x" * 4096)
        return httpx.Response(200, text="small")

    http_client, _ = _recording_client(handler)

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        big_result, small_result = await crawler.crawl_pinned(
            _plain_crawl_request(
                "https://big.example/page", "https://small.example/page"
            ),
            [
                _pinned_target("https://big.example/page", "big.example"),
                _pinned_target("https://small.example/page", "small.example"),
            ],
        )

    assert big_result.error is not None
    assert big_result.error.code == ProxyErrorCode.RESPONSE_TOO_LARGE.value
    assert big_result.raw is None
    assert small_result.error is None
    assert small_result.content == "small"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__stops_gzip_bomb_at_decoded_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a gzip bomb is stopped by the decoded-size limit.
    Why this matters: The compressed body is tiny, so only the decoded size
        reveals the memory it would consume.
    Setup summary: 64 KiB cap; 4 MiB of zeros gzipped; assert
        RESPONSE_TOO_LARGE for the URL.
    """
    _cap_crawler_bodies(monkeypatch, max_kib=64)
    bomb = gzip.compress(b"\0" * (4 * 1024 * 1024))
    http_client, _ = _recording_client(
        lambda _: httpx.Response(
            200,
            headers={"content-encoding": "gzip", "content-type": "text/html"},
            content=bomb,
        ),
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        (result,) = await crawler.crawl_pinned(
            _plain_crawl_request("https://bomb.example/page"),
            [_pinned_target("https://bomb.example/page", "bomb.example")],
        )

    assert result.error is not None
    assert result.error.code == ProxyErrorCode.RESPONSE_TOO_LARGE.value


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__rejects_unrequested_content_encoding() -> None:
    """
    Purpose: Verify encodings other than gzip/deflate are rejected unread.
    Why this matters: brotli and zstd allow far larger decompression ratios.
    Setup summary: Response with content-encoding br; assert a per-URL error
        naming the encoding.
    """
    http_client, _ = _recording_client(
        lambda _: httpx.Response(
            200, headers={"content-encoding": "br"}, content=b"\x00\x01"
        ),
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        (result,) = await crawler.crawl_pinned(
            _plain_crawl_request("https://br.example/page"),
            [_pinned_target("https://br.example/page", "br.example")],
        )

    assert result.error is not None
    assert result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value
    assert "br" in result.error.message


@pytest.mark.ai
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_encoding",
    ["gzip, gzip", "deflate, gzip", "gzip, identity, deflate"],
)
async def test_crawl_pinned__rejects_stacked_compression__only_for_affected_url(
    content_encoding: str,
) -> None:
    """
    Purpose: Verify responses with more than one compressing layer are rejected.
    Why this matters: httpx decodes all layers in one step, so a second layer
        inflates past the decoded-size limit before it can be checked.
    Setup summary: One URL streams a body with a stacked content-encoding,
        another a plain body; assert only the stacked URL errors, its body is
        never read, and the other still succeeds.
    """
    stacked_body_read: list[bool] = []

    async def stacked_body() -> AsyncIterator[bytes]:
        stacked_body_read.append(True)
        yield gzip.compress(gzip.compress(b"\0" * 1024))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["Host"] == "stacked.example":
            return httpx.Response(
                200,
                headers={"content-encoding": content_encoding},
                content=stacked_body(),
            )
        return httpx.Response(200, text="plain")

    http_client, _ = _recording_client(handler)

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        stacked_result, plain_result = await crawler.crawl_pinned(
            _plain_crawl_request(
                "https://stacked.example/page", "https://plain.example/page"
            ),
            [
                _pinned_target("https://stacked.example/page", "stacked.example"),
                _pinned_target("https://plain.example/page", "plain.example"),
            ],
        )

    assert stacked_result.error is not None
    assert stacked_result.error.code == ProxyErrorCode.UPSTREAM_ERROR.value
    assert "Unsupported content encoding" in stacked_result.error.message
    assert stacked_result.raw is None
    assert stacked_body_read == []
    assert plain_result.error is None
    assert plain_result.content == "plain"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__decodes_gzip_body__when_under_limit() -> None:
    """
    Purpose: Verify normal gzip pages are decoded and returned as text.
    Why this matters: Most sites compress; the cap must not break them.
    Setup summary: Gzipped HTML within the default cap; assert decoded content.
    """
    http_client, _ = _recording_client(
        lambda _: httpx.Response(
            200,
            headers={
                "content-encoding": "gzip",
                "content-type": "text/html; charset=utf-8",
            },
            content=gzip.compress("<p>Grüezi</p>".encode()),
        ),
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        (result,) = await crawler.crawl_pinned(
            _plain_crawl_request("https://gzip.example/page"),
            [_pinned_target("https://gzip.example/page", "gzip.example")],
        )

    assert result.error is None
    assert result.content is not None
    assert "Grüezi" in result.content


def _set_crawl_budget(monkeypatch: pytest.MonkeyPatch, *, max_kib: int) -> None:
    import unique_search_proxy_client.web.core.crawlers.basic.service as service_module

    monkeypatch.setattr(
        service_module,
        "request_limits_settings",
        service_module.request_limits_settings.model_copy(
            update={"max_crawl_response_kib": max_kib},
        ),
    )


def _sequential_crawl_request(*urls: str) -> BaseModel:
    return parse_crawl_request(
        {
            "urls": list(urls),
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "maxConcurrentRequests": 1,
        },
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__fails_url_that_overruns_crawl_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify the URL that overruns the crawl budget fails on its own.
    Why this matters: The budget bounds one request's total retained bodies.
    Setup summary: 1 KiB budget, sequential fetches of 800, 800 and 100 byte
        bodies; assert the second fails and the third still fits once the
        failed body's bytes are released.
    """
    _set_crawl_budget(monkeypatch, max_kib=1)
    sizes = {"a.example": 800, "b.example": 800, "c.example": 100}
    http_client, _ = _recording_client(
        lambda request: httpx.Response(200, text="x" * sizes[request.headers["Host"]]),
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        first, second, third = await crawler.crawl_pinned(
            _sequential_crawl_request(
                "https://a.example/", "https://b.example/", "https://c.example/"
            ),
            [
                _pinned_target("https://a.example/", "a.example"),
                _pinned_target("https://b.example/", "b.example"),
                _pinned_target("https://c.example/", "c.example"),
            ],
        )

    assert first.error is None
    assert second.error is not None
    assert second.error.code == ProxyErrorCode.RESPONSE_TOO_LARGE.value
    assert third.error is None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__skips_fetch__when_crawl_budget_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify URLs are not fetched once the crawl budget is used up.
    Why this matters: Avoids network work whose result would be discarded.
    Setup summary: 1 KiB budget, first body exactly 1 KiB; assert the second
        URL errors with RESPONSE_TOO_LARGE and was never requested.
    """
    _set_crawl_budget(monkeypatch, max_kib=1)
    http_client, requests = _recording_client(
        lambda _: httpx.Response(200, text="x" * 1024),
    )

    async with http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        first, second = await crawler.crawl_pinned(
            _sequential_crawl_request("https://a.example/", "https://b.example/"),
            [
                _pinned_target("https://a.example/", "a.example"),
                _pinned_target("https://b.example/", "b.example"),
            ],
        )

    assert first.error is None
    assert second.error is not None
    assert second.error.code == ProxyErrorCode.RESPONSE_TOO_LARGE.value
    assert len(requests) == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__clamps_fetch_concurrency__when_above_ceiling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify maxConcurrentRequests cannot exceed the server ceiling.
    Why this matters: Concurrent fetches multiply in-flight sockets and bytes.
    Setup summary: Ceiling 2, request 10 concurrent over 6 URLs with a
        handler that yields; assert at most 2 fetches were in flight.
    """
    import asyncio

    import unique_search_proxy_client.web.core.crawlers.basic.service as service_module

    monkeypatch.setattr(
        service_module,
        "request_limits_settings",
        service_module.request_limits_settings.model_copy(
            update={"max_concurrent_fetches": 2},
        ),
    )
    in_flight = 0
    peak = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return httpx.Response(200, text="ok")

    urls = [f"https://{name}.example/" for name in "abcdef"]
    request = parse_crawl_request(
        {
            "urls": urls,
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "maxConcurrentRequests": 10,
        },
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        crawler = BasicCrawlerService(http_client=client)
        results = await crawler.crawl_pinned(
            request,
            [_pinned_target(url, url.split("/")[2]) for url in urls],
        )

    assert all(result.error is None for result in results)
    assert peak == 2
