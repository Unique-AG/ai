from __future__ import annotations

import asyncio
from typing import Any, Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.url_safety.gate import UrlSafetyGateResult

_HTML_PAGE = """
<html><head><title>Test</title></head>
<body><h1>Hello</h1><p>World</p></body></html>
"""


def _is_example_com_request(request: httpx.Request) -> bool:
    host_header = request.headers.get("host", "")
    if isinstance(host_header, bytes):
        host_header = host_header.decode()
    url = str(request.url)
    return "example.com" in host_header or "example.com" in url


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, Any, None]:
    get_calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        get_calls.append(request)
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
        test_client.get_calls = get_calls  # type: ignore[attr-defined]
        yield test_client


@pytest.mark.ai
def test_crawl_url_safety__blocks_localhost_without_upstream_fetch(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["http://127.0.0.1:8080"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 1
    result = payload["results"][0]
    assert result["error"]["code"] == ProxyErrorCode.FORBIDDEN_TARGET.value
    assert "private" in result["error"]["message"].lower()
    assert client.get_calls == []  # type: ignore[attr-defined]


@pytest.mark.ai
def test_crawl_url_safety__mixed_batch_preserves_order(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/crawl",
        json={
            "urls": [
                "http://127.0.0.1:8080",
                "https://example.com/article",
            ],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["error"]["code"] == ProxyErrorCode.FORBIDDEN_TARGET.value
    assert results[1]["error"] is None
    assert "Hello" in results[1]["content"]


@pytest.mark.ai
def test_crawl_url_safety__pins_basic_fetch_to_resolved_ip(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    get_calls: list[httpx.Request] = client.get_calls  # type: ignore[attr-defined]
    assert len(get_calls) == 1
    request = get_calls[0]
    assert str(request.url).startswith("https://93.184.216.34/")
    assert request.headers["Host"] == "example.com"
    assert request.extensions["sni_hostname"] == "example.com"


@pytest.mark.ai
def test_crawl_url_safety__gate_respects_request_timeout(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def slow_gate(_urls: list[str]) -> UrlSafetyGateResult:
        await asyncio.sleep(2)
        return UrlSafetyGateResult(allowed_targets=[], blocked_by_index={})

    monkeypatch.setattr(
        "unique_search_proxy_client.web.api.v1.crawl.apply_url_safety_gate",
        slow_gate,
    )

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
    payload = response.json()
    assert payload["error"]["code"] == ProxyErrorCode.UPSTREAM_TIMEOUT.value


@pytest.mark.ai
def test_crawl_url_safety__disabled_bypasses_gate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import unique_search_proxy_core.url_safety.service as service_module

    monkeypatch.setattr(
        service_module,
        "url_safety_settings",
        service_module.url_safety_settings.model_copy(update={"enabled": False}),
    )

    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["http://127.0.0.1:8080"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert (
        result["error"] is None
        or result["error"]["code"] != ProxyErrorCode.FORBIDDEN_TARGET.value
    )
    assert client.get_calls  # type: ignore[attr-defined]
