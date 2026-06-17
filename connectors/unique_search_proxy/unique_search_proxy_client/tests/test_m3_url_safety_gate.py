from __future__ import annotations

from typing import Any, Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app

_HTML_PAGE = """
<html><head><title>Test</title></head>
<body><h1>Hello</h1><p>World</p></body></html>
"""


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, Any, None]:
    head_calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        head_calls.append(url)
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
        test_client.head_calls = head_calls  # type: ignore[attr-defined]
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
    assert client.head_calls == []  # type: ignore[attr-defined]


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
    assert client.head_calls  # type: ignore[attr-defined]
