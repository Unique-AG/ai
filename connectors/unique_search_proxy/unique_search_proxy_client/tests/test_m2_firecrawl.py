from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.schema import ProxyErrorCode, WebSearchResults
from unique_search_proxy_core.search_engines.firecrawl.schema import (
    FirecrawlSearchRequest,
)

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.search_engines.firecrawl.service import (
    FirecrawlSearchService,
)

_SERVICE_CREDENTIALS = (
    "unique_search_proxy_client.web.core.search_engines.firecrawl.service.credentials"
)


def _web_item(*, url: str = "https://example.com/page") -> dict[str, Any]:
    return {
        "url": url,
        "title": "Example",
        "description": "An example description",
    }


def _firecrawl_payload(**data: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "success": True,
        "data": data or {"web": [_web_item()]},
        "creditsUsed": 3,
    }


def _use_firecrawl_credentials(
    monkeypatch: pytest.MonkeyPatch,
    *,
    zero_data_retention: str = "none",
) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("FIRECRAWL_ZERO_DATA_RETENTION", zero_data_retention)
    from unique_search_proxy_client.web.settings.providers.firecrawl import (
        _get_firecrawl_crawl_credentials,
    )

    monkeypatch.setattr(_SERVICE_CREDENTIALS, _get_firecrawl_crawl_credentials())


@pytest.fixture
def firecrawl_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_firecrawl_credentials(monkeypatch)


def _firecrawl_request(**fields: Any) -> FirecrawlSearchRequest:
    return FirecrawlSearchRequest.model_validate(
        {
            "query": "hello",
            "fetch_size": 10,
            "timeout": 60,
            **fields,
        },
    )


async def _search(
    handler: Callable[[httpx.Request], httpx.Response],
    **fields: Any,
) -> WebSearchResults:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        engine = FirecrawlSearchService(http_client=client)
        _raw, curated = await engine.search(_firecrawl_request(**fields))
    return curated


class TestFirecrawlSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__maps_web_result__to_url_title_and_preview(
        self, firecrawl_env: None
    ) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("Authorization")
            captured["url"] = str(request.url)
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_firecrawl_payload())

        curated = await _search(handler)

        assert captured["auth"] == "Bearer test-key"
        assert captured["url"] == "https://api.firecrawl.dev/v2/search"
        assert captured["json"]["query"] == "hello"
        assert captured["json"]["limit"] == 10
        assert len(curated) == 1
        assert curated.results[0].url == "https://example.com/page"
        assert curated.results[0].title == "Example"
        assert curated.results[0].snippet == "An example description"
        assert not curated.results[0].content

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__reads_news_items__when_news_source_is_requested(
        self, firecrawl_env: None
    ) -> None:
        payload = _firecrawl_payload(
            news=[
                {
                    "url": "https://news.example.com/a",
                    "title": "A",
                    "description": "From description",
                    "snippet": None,
                },
                {
                    "url": "https://news.example.com/b",
                    "title": "B",
                    "snippet": "From snippet",
                },
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler, sources="web_and_news")

        assert [result.snippet for result in curated.results] == [
            "From description",
            "From snippet",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__returns_long_previews_whole(
        self, firecrawl_env: None
    ) -> None:
        long_text = "price " * 4000
        payload = _firecrawl_payload(
            web=[
                {
                    "url": "https://example.com/long",
                    "title": "L",
                    "description": long_text,
                },
                {
                    "url": "https://example.com/short",
                    "title": "S",
                    "description": "Short.",
                },
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler)
        long_snippet, short_snippet = (r.snippet for r in curated.results)

        assert long_snippet == long_text
        assert short_snippet == "Short."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__keeps_news__when_web_fills_fetch_size(
        self, firecrawl_env: None
    ) -> None:
        payload = _firecrawl_payload(
            web=[_web_item(url=f"https://example.com/web-{i}") for i in range(5)],
            news=[
                {"url": f"https://example.com/news-{i}", "title": "N"} for i in range(5)
            ],
        )

        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        curated = await _search(handler, sources="web_and_news", fetch_size=5)

        assert [result.url for result in curated.results] == [
            "https://example.com/web-0",
            "https://example.com/news-0",
            "https://example.com/web-1",
            "https://example.com/news-1",
            "https://example.com/web-2",
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("deployed", "requested", "expected"),
        [("none", "zdr", ["zdr"]), ("zdr", "anon", ["zdr"]), ("anon", "zdr", ["zdr"])],
        ids=["raises-none", "cannot-lower", "raises-anon"],
    )
    async def test_search__sends_the_stricter_enterprise_mode__of_env_and_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
        deployed: str,
        requested: str,
        expected: list[str],
    ) -> None:
        _use_firecrawl_credentials(monkeypatch, zero_data_retention=deployed)
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_firecrawl_payload())

        await _search(handler, zero_data_retention=requested)

        assert captured["json"]["enterprise"] == expected

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__keeps_query_out_of_logs__on_success(
        self,
        firecrawl_env: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_firecrawl_payload())

        with caplog.at_level(logging.INFO):
            await _search(handler, query="confidential-marker")

        assert "confidential-marker" not in caplog.text

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_empty_results__when_provider_returns_none(
        self, firecrawl_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_firecrawl_payload(web=[]))

        with pytest.raises(EmptySearchResultsError, match="no results"):
            await _search(handler)

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [401, 402, 403])
    async def test_search__raises_non_retryable_upstream_error__on_account_error(
        self, firecrawl_env: None, status_code: int
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code,
                json={"success": False, "error": "ZDR search is not enabled"},
            )

        with pytest.raises(UpstreamError, match="ZDR search is not enabled") as exc:
            await _search(handler)

        assert exc.value.retryable is False

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_upstream_error__when_success_flag_is_false(
        self, firecrawl_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"success": False, "error": "bad query"})

        with pytest.raises(UpstreamError, match="bad query"):
            await _search(handler)

    @pytest.mark.ai
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("body", "message"),
        [(b"[]", "must be a JSON object"), (b"<html>busy</html>", "invalid JSON")],
        ids=["json-array", "not-json"],
    )
    async def test_search__raises_upstream_error__when_answer_is_not_a_json_object(
        self,
        firecrawl_env: None,
        body: bytes,
        message: str,
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body)

        with pytest.raises(UpstreamError, match=message):
            await _search(handler)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__skips_malformed_items__and_reports_a_malformed_result(
        self, firecrawl_env: None
    ) -> None:
        mixed = _firecrawl_payload(
            web=[{"metadata": 1}, {"url": 7}, _web_item()], news=1
        )
        broken = _firecrawl_payload(
            web=[{"url": "https://example.com", "title": ["not", "text"]}]
        )

        curated = await _search(
            lambda _request: httpx.Response(200, json=mixed), sources="web_and_news"
        )

        assert [result.url for result in curated.results] == [
            "https://example.com/page"
        ]
        with pytest.raises(UpstreamError, match="unexpected shape"):
            await _search(lambda _request: httpx.Response(200, json=broken))

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__drops_results_on_excluded_subdomain__of_an_included_host(
        self, firecrawl_env: None
    ) -> None:
        captured: dict[str, Any] = {}
        payload = _firecrawl_payload(
            web=[
                {"url": "https://private.example.com/a", "title": "Blocked"},
                {"url": "https://www.example.com/b", "title": "Allowed"},
            ],
        )

        def handler(request: httpx.Request) -> httpx.Response:
            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=payload)

        curated = await _search(
            handler,
            include_domains=["example.com"],
            exclude_domains=["private.example.com"],
        )

        assert captured["json"]["includeDomains"] == ["example.com"]
        assert "excludeDomains" not in captured["json"]
        assert [result.url for result in curated.results] == [
            "https://www.example.com/b"
        ]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_rate_limited__on_429(
        self, firecrawl_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "8"})

        with pytest.raises(RateLimitedError) as exc_info:
            await _search(handler)

        assert exc_info.value.retry_after_seconds == 8

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search__raises_upstream_timeout__when_request_times_out(
        self, firecrawl_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        with pytest.raises(UpstreamTimeoutError):
            await _search(handler, timeout=1)


class TestFirecrawlSearchEndpoint:
    @pytest.mark.ai
    def test_search_route__returns_503__when_firecrawl_is_not_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FIRECRAWL_API_KEY", "NOT_PROVIDED")
        from unique_search_proxy_client.web.settings.providers.firecrawl import (
            _get_firecrawl_crawl_credentials,
        )

        monkeypatch.setattr(_SERVICE_CREDENTIALS, _get_firecrawl_crawl_credentials())

        with TestClient(create_app()) as client:
            resp = client.post(
                "/v1/search",
                json={"engine": "firecrawl", "query": "hello", "fetchSize": 3},
            )

        assert resp.status_code == 503
        assert (
            resp.json()["error"]["code"] == ProxyErrorCode.ENGINE_NOT_CONFIGURED.value
        )
