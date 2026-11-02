from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Generator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.config_types import parse_crawl_request
from unique_search_proxy_core.schema import ProxyErrorCode
from unique_search_proxy_core.url_safety import (
    ResolvedCrawlTarget,
    UrlSafetyOutcome,
    UrlSafetyService,
)

import unique_search_proxy_client.web.api.v1.crawl as crawl_module
from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.crawlers.basic.service import (
    BasicCrawlerService,
)
from unique_search_proxy_client.web.core.url_safety import gate as gate_module
from unique_search_proxy_client.web.core.url_safety.gate import (
    AllowedCrawlTarget,
    apply_url_safety_gate,
)

_HTML_PAGE = "<html><body><h1>Hello</h1><p>World</p></body></html>"
_HANGING_HOST = "hang.example"
_HANG_SECONDS = 30
_SLOW_TO_CANCEL_HOST = "slow-cancel.example"
_SLOW_CANCEL_SECONDS = 1.0


def _host(request: httpx.Request) -> str:
    host_header = request.headers.get("host", "")
    if isinstance(host_header, bytes):
        host_header = host_header.decode()
    return host_header.split(":", 1)[0] or request.url.host


async def _origin(request: httpx.Request) -> httpx.Response:
    host = _host(request)
    if host == _HANGING_HOST:
        await asyncio.sleep(_HANG_SECONDS)
    elif host == _SLOW_TO_CANCEL_HOST:
        try:
            await asyncio.sleep(_HANG_SECONDS)
        except asyncio.CancelledError:
            await asyncio.sleep(_SLOW_CANCEL_SECONDS)
            raise
    return httpx.Response(
        200,
        text=_HTML_PAGE,
        headers={"content-type": "text/html; charset=utf-8"},
    )


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


@pytest.fixture
def hanging_url_safety_check(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Make URL safety validation hang for the hanging host only.

    Returns the URLs validation was asked to check, in call order.
    """
    validate = UrlSafetyService.validate_urls_individually
    checked_urls: list[str] = []

    async def hang_for_one_host(
        urls: list[str],
        *,
        redirect_http_client: httpx.AsyncClient | None = None,
    ) -> list[UrlSafetyOutcome]:
        checked_urls.extend(urls)
        if any(_HANGING_HOST in url for url in urls):
            await asyncio.sleep(_HANG_SECONDS)
        return await validate(urls, redirect_http_client=redirect_http_client)

    monkeypatch.setattr(
        gate_module.UrlSafetyService,
        "validate_urls_individually",
        hang_for_one_host,
    )
    return checked_urls


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, Any, None]:
    from unique_search_proxy_client.web.core.client.service import HttpClientRegistry

    async def mock_create_registry() -> HttpClientRegistry:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(_origin))
        return HttpClientRegistry.fixed(http_client)

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_registry",
        mock_create_registry,
    )
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__returns_finished_pages__when_one_page_misses_deadline() -> (
    None
):
    """
    Purpose: Verify a page still running at the deadline fails alone.
    Why this matters: One hanging site must not cost the sources of every other
        page in the batch.
    Setup summary: Three targets, the middle one hangs; deadline 0.2s ahead;
        assert the other two have content and the hanging one has a per-URL
        UPSTREAM_TIMEOUT, in request order.
    """
    request = parse_crawl_request(
        {
            "urls": [
                "https://a.example/",
                f"https://{_HANGING_HOST}/",
                "https://b.example/",
            ],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )
    targets = [
        _pinned_target("https://a.example/", "a.example"),
        _pinned_target(f"https://{_HANGING_HOST}/", _HANGING_HOST),
        _pinned_target("https://b.example/", "b.example"),
    ]

    async with httpx.AsyncClient(transport=httpx.MockTransport(_origin)) as http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        results = await crawler.crawl_pinned(
            request,
            targets,
            deadline=asyncio.get_running_loop().time() + 0.2,
        )

    assert [result.url for result in results] == [
        target.display_url for target in targets
    ]
    assert results[0].error is None
    assert results[0].content is not None
    assert results[1].error is not None
    assert results[1].error.code == ProxyErrorCode.UPSTREAM_TIMEOUT.value
    assert results[1].content is None
    assert results[2].error is None
    assert results[2].content is not None


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_pinned__logs_one_warning_without_urls__when_pages_miss_deadline(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify missed pages produce one warning with a count and no URLs.
    Why this matters: URLs can contain CID, and one line per hanging page floods
        the logs when many pages in a batch stall.
    Setup summary: Two hanging targets and one fast target; deadline 0.2s ahead;
        assert a single deadline warning with pages=2 and no hostnames.
    """
    hanging_urls = [f"https://{_HANGING_HOST}/one", f"https://{_HANGING_HOST}/two"]
    urls = ["https://a.example/", *hanging_urls]
    request = parse_crawl_request(
        {
            "urls": urls,
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )
    targets = [
        _pinned_target(urls[0], "a.example"),
        *[_pinned_target(url, _HANGING_HOST) for url in hanging_urls],
    ]
    monkeypatch.setattr(
        logging.getLogger("unique_search_proxy_client"), "propagate", True
    )
    caplog.set_level(logging.WARNING)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_origin)) as http_client:
        crawler = BasicCrawlerService(http_client=http_client)
        await crawler.crawl_pinned(
            request,
            targets,
            deadline=asyncio.get_running_loop().time() + 0.2,
        )

    deadline_warnings = [
        record.getMessage()
        for record in caplog.records
        if "missed the request deadline" in record.getMessage()
    ]
    assert deadline_warnings == [
        "Basic crawl missed the request deadline timeout=10s pages=2"
    ]
    assert _HANGING_HOST not in caplog.text
    assert "a.example" not in caplog.text


@pytest.mark.ai
def test_crawl__returns_partial_results__when_one_page_hangs(
    client: TestClient,
) -> None:
    """
    Purpose: Verify the endpoint answers 200 with per-URL results when a page hangs.
    Why this matters: A whole-request 504 made callers drop every page of the
        batch (UN-28319).
    Setup summary: Two URLs, one hangs longer than the 1s timeout; assert 200,
        content for the fast URL and UPSTREAM_TIMEOUT for the hanging one.
    """
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article", f"https://{_HANGING_HOST}/"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 1,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    fast, hanging = response.json()["results"]
    assert fast["error"] is None
    assert "Hello" in fast["content"]
    assert hanging["error"]["code"] == ProxyErrorCode.UPSTREAM_TIMEOUT.value
    assert hanging["content"] is None


@pytest.mark.ai
def test_crawl__returns_partial_results__when_cancelled_page_finishes_late(
    client: TestClient,
) -> None:
    """
    Purpose: Verify pages that finished are returned even when cancelling the rest runs late.
    Why this matters: Under load a worker can finish cancelling pages seconds
        after the deadline; that must delay the response, not turn it into a 504.
    Setup summary: Timeout 1s; one page takes 1s to unwind after cancellation,
        past the request timeout; assert 200 with the other page's content.
    """
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article", f"https://{_SLOW_TO_CANCEL_HOST}/"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 1,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    fast, slow = response.json()["results"]
    assert "Hello" in fast["content"]
    assert slow["error"]["code"] == ProxyErrorCode.UPSTREAM_TIMEOUT.value


@pytest.mark.ai
def test_crawl__fails_request_at_timeout__when_unpinned_crawler_hangs(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify crawlers without pinned egress still fail the request at its timeout.
    Why this matters: Tavily, Jina and Firecrawl have no per-URL deadline; the
        later safety net must not give them extra time.
    Setup summary: A crawler service whose crawl hangs; timeout 1s; assert 504
        well before the safety net would fire.
    """

    class HangingCrawler:
        async def crawl(self, _request: object) -> list[object]:
            await asyncio.sleep(_HANG_SECONDS)
            return []

    monkeypatch.setattr(
        crawl_module,
        "get_crawler_service",
        lambda *_args, **_kwargs: HangingCrawler(),
    )

    started = time.monotonic()
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 1,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 504
    assert time.monotonic() - started < 3


@pytest.mark.ai
@pytest.mark.usefixtures("hanging_url_safety_check")
def test_crawl__returns_per_url_results__when_url_safety_check_hangs(
    client: TestClient,
) -> None:
    """
    Purpose: Verify a hanging URL safety check yields per-URL results, not a 504.
    Why this matters: The gate shares the request deadline; a slow redirect
        probe must not turn into a whole-request 504.
    Setup summary: Validation hangs for the second URL; timeout 1s; assert
        200 with one result per URL and UPSTREAM_TIMEOUT for the hanging one.
    """
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article", f"https://{_HANGING_HOST}/"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 1,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[1]["error"]["code"] == ProxyErrorCode.UPSTREAM_TIMEOUT.value


@pytest.mark.ai
@pytest.mark.asyncio
async def test_apply_url_safety_gate__times_out_unchecked_urls__at_deadline(
    hanging_url_safety_check: list[str],
) -> None:
    """
    Purpose: Verify the gate stops at the deadline and fails unchecked URLs alone.
    Why this matters: Checks run one URL at a time, so a slow check must not
        hold the request past its deadline, and timed-out URLs are not blocked.
    Setup summary: Validation hangs for the second of three URLs; deadline
        0.2s ahead; assert the first is allowed, the third is never checked,
        and the last two are timed out rather than blocked.
    """
    urls = ["https://a.example/", f"https://{_HANGING_HOST}/", "https://b.example/"]

    async with httpx.AsyncClient() as http_client:
        gate = await apply_url_safety_gate(
            urls,
            redirect_http_client=http_client,
            deadline=asyncio.get_running_loop().time() + 0.2,
        )

    assert [target.display_url for target in gate.allowed_targets] == [urls[0]]
    assert hanging_url_safety_check == urls[:2]
    assert gate.blocked_by_index == {}
    assert sorted(gate.timed_out_by_index) == [1, 2]
    hanging_error = gate.timed_out_by_index[1].error
    unchecked_error = gate.timed_out_by_index[2].error
    assert hanging_error is not None
    assert hanging_error.code == ProxyErrorCode.UPSTREAM_TIMEOUT.value
    assert unchecked_error is not None
    assert unchecked_error.code == ProxyErrorCode.UPSTREAM_TIMEOUT.value
