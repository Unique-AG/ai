from __future__ import annotations

from typing import Any

import httpx
import pytest
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    EngineNotConfiguredError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.search_engines.brave.schema import BraveRequest

from unique_search_proxy_client.web.core.search_engines.brave.service import (
    BraveSearchService,
)


def _brave_web_payload(*, url: str = "https://example.com/page") -> dict[str, Any]:
    return {
        "web": {
            "results": [
                {
                    "url": url,
                    "title": "Example",
                    "description": "An example snippet",
                },
            ],
        },
    }


@pytest.fixture
def brave_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv(
        "BRAVE_SEARCH_API_ENDPOINT",
        "https://api.search.brave.com/res/v1/web/search",
    )


def _brave_request(**fields: Any) -> BraveRequest:
    return BraveRequest.model_validate(
        {
            "query": "hello",
            "fetch_size": 10,
            "timeout": 30,
            **fields,
        },
    )


class TestBraveSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_maps_results(self, brave_env: None) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["X-Subscription-Token"] == "test-key"
            assert request.url.params.get("q") == "hello"
            return httpx.Response(200, json=_brave_web_payload())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = BraveSearchService(http_client=client)
            _raw, curated = await engine.search(_brave_request())

        assert len(curated) == 1
        assert curated.results[0].url == "https://example.com/page"
        assert curated.results[0].title == "Example"
        assert curated.results[0].snippet == "An example snippet"

    @pytest.mark.ai
    def test_extract_web_results_ignores_news_bucket(self) -> None:
        payload = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com/web",
                        "title": "Web",
                        "description": "web snippet",
                    },
                ],
            },
            "news": {
                "results": [
                    {
                        "url": "https://example.com/news",
                        "title": "News",
                        "description": "news snippet",
                    },
                ],
            },
        }
        results = BraveSearchService._extract_web_results(None, payload)  # type: ignore[arg-type]
        assert len(results) == 1
        assert results[0].url == "https://example.com/web"

    def test_extract_results_maps_description_not_summarizer(self) -> None:
        payload = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "Example",
                        "description": "Main excerpt",
                    },
                ],
            },
            "summarizer": {"key": "abc123"},
        }
        results = BraveSearchService._extract_web_results(None, payload)  # type: ignore[arg-type]
        assert results[0].snippet == "Main excerpt"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_pagination_uses_offset_and_count(self, brave_env: None) -> None:
        captured: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(
                (
                    request.url.params.get("offset", ""),
                    request.url.params.get("count", ""),
                ),
            )
            return httpx.Response(200, json=_brave_web_payload())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = BraveSearchService(http_client=client)
            await engine.search(_brave_request(fetch_size=25))

        assert captured == [("0", "20"), ("1", "5")]

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_empty_results_raises(self, brave_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"web": {"results": []}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = BraveSearchService(http_client=client)
            with pytest.raises(EmptySearchResultsError, match="no results"):
                await engine.search(_brave_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_missing_credentials_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "NOT_PROVIDED")

        engine = BraveSearchService()
        with pytest.raises(EngineNotConfiguredError):
            await engine.search(_brave_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_upstream_error_on_non_success(self, brave_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"message": "backend"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = BraveSearchService(http_client=client)
            with pytest.raises(UpstreamError, match="500"):
                await engine.search(_brave_request(query="fail"))

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_rate_limited_raises_429(self, brave_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "8"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = BraveSearchService(http_client=client)
            with pytest.raises(RateLimitedError) as exc_info:
                await engine.search(_brave_request(query="slow"))
            assert exc_info.value.retry_after_seconds == 8

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_timeout_maps_to_upstream_timeout(self, brave_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = BraveSearchService(http_client=client)
            with pytest.raises(UpstreamTimeoutError):
                await engine.search(_brave_request(query="slow", timeout=1))
