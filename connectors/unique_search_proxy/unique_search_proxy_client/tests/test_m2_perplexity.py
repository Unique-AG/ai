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
from unique_search_proxy_core.search_engines.perplexity.schema import (
    PerplexitySearchRequest,
)

from unique_search_proxy_client.web.core.search_engines.perplexity.service import (
    PerplexitySearchService,
)


def _perplexity_payload(*, url: str = "https://example.com/page") -> dict[str, Any]:
    return {
        "results": [
            {
                "url": url,
                "title": "Example",
                "snippet": "An example snippet",
            },
        ],
    }


@pytest.fixture
def perplexity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERPLEXITY_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv(
        "PERPLEXITY_SEARCH_API_ENDPOINT",
        "https://api.perplexity.ai/search",
    )


def _perplexity_request(**fields: Any) -> PerplexitySearchRequest:
    return PerplexitySearchRequest.model_validate(
        {
            "query": "hello",
            "fetch_size": 10,
            "timeout": 30,
            **fields,
        },
    )


class TestPerplexitySearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_maps_results(self, perplexity_env: None) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("Authorization")
            captured["body"] = httpx.Request(
                method=request.method,
                url=request.url,
                content=request.content,
                headers={"content-type": "application/json"},
            )
            import json

            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_perplexity_payload())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = PerplexitySearchService(http_client=client)
            _raw, curated = await engine.search(_perplexity_request())

        assert captured["auth"] == "Bearer test-key"
        assert captured["json"]["query"] == "hello"
        assert captured["json"]["max_results"] == 10
        assert len(curated) == 1
        assert curated.results[0].url == "https://example.com/page"
        assert curated.results[0].title == "Example"
        assert curated.results[0].snippet == "An example snippet"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_clamps_max_results_to_api_limit(self, perplexity_env: None) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured["json"] = json.loads(request.content.decode())
            return httpx.Response(200, json=_perplexity_payload())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = PerplexitySearchService(http_client=client)
            await engine.search(_perplexity_request(fetch_size=50))

        assert captured["json"]["max_results"] == 20

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_empty_results_raises(self, perplexity_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"results": []})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = PerplexitySearchService(http_client=client)
            with pytest.raises(EmptySearchResultsError, match="no results"):
                await engine.search(_perplexity_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_missing_credentials_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PERPLEXITY_SEARCH_API_KEY", "NOT_PROVIDED")

        engine = PerplexitySearchService()
        with pytest.raises(EngineNotConfiguredError):
            await engine.search(_perplexity_request())

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_upstream_error_on_non_success(self, perplexity_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": {"detail": "backend"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = PerplexitySearchService(http_client=client)
            with pytest.raises(UpstreamError, match="500"):
                await engine.search(_perplexity_request(query="fail"))

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_rate_limited_raises_429(self, perplexity_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "8"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = PerplexitySearchService(http_client=client)
            with pytest.raises(RateLimitedError) as exc_info:
                await engine.search(_perplexity_request(query="slow"))
            assert exc_info.value.retry_after_seconds == 8

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_timeout_maps_to_upstream_timeout(self, perplexity_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = PerplexitySearchService(http_client=client)
            with pytest.raises(UpstreamTimeoutError):
                await engine.search(_perplexity_request(query="slow", timeout=1))
