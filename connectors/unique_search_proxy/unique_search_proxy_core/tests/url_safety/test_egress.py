from __future__ import annotations

import pytest
from unique_search_proxy_core.url_safety import ResolvedCrawlTarget, pinned_httpx_get_args


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
