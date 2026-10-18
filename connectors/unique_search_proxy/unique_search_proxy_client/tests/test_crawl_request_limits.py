from __future__ import annotations

import asyncio
from typing import Any, Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.errors import RateLimitedError
from unique_search_proxy_core.schema import ProxyErrorCode

import unique_search_proxy_client.web.api.v1.crawl as crawl_module
from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.client.service import HttpClientRegistry
from unique_search_proxy_client.web.core.crawl_limiter import CrawlLimiter
from unique_search_proxy_client.web.core.url_safety.gate import UrlSafetyGateResult


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


@pytest.mark.ai
async def test_crawl_limiter__rejects__when_all_slots_taken() -> None:
    """
    Purpose: Verify the limiter fails fast instead of queueing.
    Why this matters: Queued crawls would still pile bodies up in the worker.
    Setup summary: One-slot limiter held open; assert a second slot raises
        RateLimitedError with a retry hint.
    """
    limiter = CrawlLimiter(1)

    async with limiter.slot():
        with pytest.raises(RateLimitedError) as exc_info:
            async with limiter.slot():
                pass

    assert exc_info.value.retry_after_seconds == 1


@pytest.mark.ai
async def test_crawl_limiter__frees_slot__when_crawl_raises() -> None:
    """
    Purpose: Verify a failing crawl gives its slot back.
    Why this matters: Leaked slots would turn every later crawl into a 429.
    Setup summary: One-slot limiter, raise inside the slot; assert the slot
        can be taken again.
    """
    limiter = CrawlLimiter(1)

    with pytest.raises(ValueError):
        async with limiter.slot():
            raise ValueError("boom")

    async with limiter.slot():
        pass


@pytest.mark.ai
def test_crawl__returns_429__when_worker_crawl_capacity_full(
    client: TestClient,
) -> None:
    """
    Purpose: Verify the endpoint answers 429 with Retry-After when full.
    Why this matters: Callers need a retryable signal, not a hung request.
    Setup summary: Replace the app limiter with a zero-slot one; assert 429
        RATE_LIMITED, Retry-After 1 and no upstream fetch.
    """
    client.app.state.crawl_limiter = CrawlLimiter(0)  # type: ignore[attr-defined]

    response = _crawl(client, ["https://a.example/"])

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "1"
    assert response.json()["error"]["code"] == ProxyErrorCode.RATE_LIMITED.value
    assert client.upstream_calls == []  # type: ignore[attr-defined]


@pytest.mark.ai
def test_crawl__clamps_timeout__when_above_server_ceiling(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Purpose: Verify a crawl timeout above the server ceiling is lowered.
    Why this matters: Callers must not hold a crawl slot longer than allowed.
    Setup summary: Ceiling 1s, request timeout 600s, gate sleeping 2s;
        assert 504 reporting the 1s ceiling.
    """

    async def slow_gate(
        _urls: list[str],
        *,
        redirect_http_client: object | None = None,
    ) -> UrlSafetyGateResult:
        del redirect_http_client
        await asyncio.sleep(2)
        return UrlSafetyGateResult(allowed_targets=[], blocked_by_index={})

    monkeypatch.setattr(crawl_module, "apply_url_safety_gate", slow_gate)
    monkeypatch.setattr(
        crawl_module,
        "request_limits_settings",
        crawl_module.request_limits_settings.model_copy(
            update={"max_timeout_seconds": 1},
        ),
    )

    response = client.post(
        "/v1/crawl",
        json={
            "urls": ["https://a.example/"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 600,
        },
    )

    assert response.status_code == 504
    assert "after 1s" in response.json()["error"]["message"]
