from __future__ import annotations

from typing import Any, Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.schema import ProxyErrorCode

import unique_search_proxy_client.web.api.v1.crawl as crawl_module
from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.client.service import HttpClientRegistry


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, Any, None]:
    upstream_calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        upstream_calls.append(request)
        return httpx.Response(200, text="<html><body>ok</body></html>")

    async def fixed_registry() -> HttpClientRegistry:
        return HttpClientRegistry.fixed(
            httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_registry",
        fixed_registry,
    )
    monkeypatch.setattr(
        crawl_module,
        "request_limits_settings",
        crawl_module.request_limits_settings.model_copy(
            update={"max_urls_per_crawl": 2, "max_url_length": 40},
        ),
    )

    with TestClient(create_app()) as test_client:
        test_client.upstream_calls = upstream_calls  # type: ignore[attr-defined]
        yield test_client


def _crawl(client: TestClient, urls: list[str]) -> httpx.Response:
    return client.post(
        "/v1/crawl",
        json={
            "urls": urls,
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
    )


@pytest.mark.ai
def test_crawl__returns_422__when_url_count_exceeds_limit(
    client: TestClient,
) -> None:
    """
    Purpose: Verify a crawl listing more URLs than allowed is rejected.
    Why this matters: The URL count multiplies every per-URL memory bound.
    Setup summary: Limit of 2 URLs, request 3; assert 422 VALIDATION_ERROR
        and no upstream fetch.
    """
    response = _crawl(
        client,
        ["https://a.example/", "https://b.example/", "https://c.example/"],
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == ProxyErrorCode.VALIDATION_ERROR.value
    assert "at most 2" in error["message"]
    assert client.upstream_calls == []  # type: ignore[attr-defined]


@pytest.mark.ai
def test_crawl__returns_422__when_url_exceeds_length_limit(
    client: TestClient,
) -> None:
    """
    Purpose: Verify a crawl containing an overlong URL is rejected.
    Why this matters: Unbounded URLs inflate logs, DNS work and responses.
    Setup summary: Limit of 40 characters, second URL longer; assert 422
        naming that URL's index and no upstream fetch.
    """
    response = _crawl(
        client,
        ["https://a.example/", "https://b.example/" + "x" * 40],
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == ProxyErrorCode.VALIDATION_ERROR.value
    assert "index 1" in error["message"]
    assert client.upstream_calls == []  # type: ignore[attr-defined]


@pytest.mark.ai
def test_crawl__accepts_request__when_within_url_limits(
    client: TestClient,
) -> None:
    """
    Purpose: Verify a crawl at exactly the limits is not rejected.
    Why this matters: The limits must not turn valid requests into 422s.
    Setup summary: Two URLs of at most 40 characters, pointing at a private
        address so the gate blocks them without DNS; assert 200 with
        per-URL FORBIDDEN_TARGET results.
    """
    response = _crawl(client, ["http://127.0.0.1/", "http://127.0.0.1:8080/"])

    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["error"]["code"] for r in results] == [
        ProxyErrorCode.FORBIDDEN_TARGET.value,
        ProxyErrorCode.FORBIDDEN_TARGET.value,
    ]
