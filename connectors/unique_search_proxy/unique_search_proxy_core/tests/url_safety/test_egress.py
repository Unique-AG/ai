from __future__ import annotations

import httpx
import pytest

from unique_search_proxy_core.url_safety import (
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    pinned_httpx_get_args,
    safe_pinned_httpx_get,
)


@pytest.mark.ai
def test_pinned_httpx_get_args__returns_ip_url_host_and_sni_for_https() -> None:
    target = ResolvedCrawlTarget(
        normalized_url="https://example.com/docs?q=1",
        hostname="example.com",
        resolved_ip="93.184.216.34",
        used_dns_resolution=True,
    )

    request_url, headers, extensions = pinned_httpx_get_args(target)

    assert request_url == "https://93.184.216.34/docs?q=1"
    assert headers == {"Host": "example.com"}
    assert extensions == {"sni_hostname": "example.com"}


@pytest.mark.ai
def test_pinned_httpx_get_args__omits_pinning_for_literal_ip_urls() -> None:
    target = ResolvedCrawlTarget(
        normalized_url="https://93.184.216.34/page",
        hostname="93.184.216.34",
        resolved_ip="93.184.216.34",
        used_dns_resolution=False,
    )

    request_url, headers, extensions = pinned_httpx_get_args(target)

    assert request_url == "https://93.184.216.34/page"
    assert headers == {}
    assert extensions == {}


@pytest.mark.ai
@pytest.mark.asyncio
async def test_safe_pinned_httpx_get__validates_and_repins_each_redirect(
    fake_public_dns: None,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(302, headers={"Location": "/relative"})
        if len(requests) == 2:
            return httpx.Response(
                307,
                headers={"Location": "https://redirect.example.org/final"},
            )
        return httpx.Response(200, text="ok")

    target = ResolvedCrawlTarget(
        normalized_url="https://example.com/start",
        hostname="example.com",
        resolved_ip="93.184.216.34",
        used_dns_resolution=True,
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        response = await safe_pinned_httpx_get(
            client,
            target,
            headers={"User-Agent": "safe-crawler"},
            timeout=10.0,
            max_redirect_hops=2,
        )

    assert response.status_code == 200
    assert [str(request.url) for request in requests] == [
        "https://93.184.216.34/start",
        "https://93.184.216.34/relative",
        "https://93.184.216.34/final",
    ]
    assert [request.headers["Host"] for request in requests] == [
        "example.com",
        "example.com",
        "redirect.example.org",
    ]
    assert [request.headers["User-Agent"] for request in requests] == [
        "safe-crawler",
        "safe-crawler",
        "safe-crawler",
    ]
    assert [request.extensions["sni_hostname"] for request in requests] == [
        "example.com",
        "example.com",
        "redirect.example.org",
    ]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_safe_pinned_httpx_get__blocks_private_redirect_before_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1/admin"},
        )

    target = ResolvedCrawlTarget(
        normalized_url="https://example.com/start",
        hostname="example.com",
        resolved_ip="93.184.216.34",
        used_dns_resolution=True,
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await safe_pinned_httpx_get(
                client,
                target,
                timeout=10.0,
                max_redirect_hops=10,
            )

    assert len(requests) == 1
    assert exc_info.value.blocked_targets[0].hostname == "127.0.0.1"
    assert exc_info.value.blocked_targets[0].category == "private"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_safe_pinned_httpx_get__blocks_redirects_beyond_limit(
    fake_public_dns: None,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(302, headers={"Location": "/again"})

    target = ResolvedCrawlTarget(
        normalized_url="https://example.com/start",
        hostname="example.com",
        resolved_ip="93.184.216.34",
        used_dns_resolution=True,
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CrawlTargetValidationError) as exc_info:
            await safe_pinned_httpx_get(
                client,
                target,
                timeout=10.0,
                max_redirect_hops=1,
            )

    assert len(requests) == 2
    assert exc_info.value.blocked_targets[0].category == "redirect"
    assert "Maximum redirect hop count" in exc_info.value.blocked_targets[0].reason
