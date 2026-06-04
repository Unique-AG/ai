from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.errors import (
    EmptySearchResultsError,
    EngineNotConfiguredError,
    RateLimitedError,
    UpstreamError,
    UpstreamTimeoutError,
)
from unique_search_proxy_core.schema import ProxyErrorCode
from unique_search_proxy_core.search_engines.google.schema import (
    GoogleConfig,
    GoogleSearchRequest,
)

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.search_engines.google.service import (
    GoogleSearchService,
)
from unique_search_proxy_client.web.core.search_engines.google.settings import (
    reset_google_search_settings_for_tests,
)


def _minimal_google_item() -> dict[str, Any]:
    return {
        "link": "https://example.com/page",
        "title": "Example",
        "snippet": "snippet",
    }


def _google_items_payload() -> dict[str, Any]:
    return {
        "items": [
            {
                "link": "https://Example.COM/page#frag",
                "title": "Example",
                "snippet": "An example snippet",
            },
            {
                "link": "https://example.com/other",
                "htmlTitle": "Other",
                "snippet": "Second result",
            },
        ],
    }


def _search_body(**fields: Any) -> dict[str, Any]:
    return {
        "engine": "google",
        "query": "hello",
        "fetchSize": 10,
        "timeout": 30,
        **fields,
    }


@pytest.fixture
def google_env(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_google_search_settings_for_tests()
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-cx")
    monkeypatch.setenv(
        "GOOGLE_SEARCH_API_ENDPOINT",
        "https://customsearch.googleapis.com/customsearch/v1",
    )
    yield
    reset_google_search_settings_for_tests()


@pytest.fixture
def client() -> TestClient:
    reset_google_search_settings_for_tests()
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def google_client(google_env: None) -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


class TestGoogleSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_maps_results(self, google_env: None) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=_google_items_payload())

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(
                GoogleConfig(fetch_size=5),
                http_client=client,
            )
            raw, curated = await engine.search(
                GoogleSearchRequest(query="hello"),
                timeout=30,
            )

        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResults,
        )

        assert isinstance(raw, SearchEngineRaw)
        assert len(raw.pages) == 1
        assert len(curated) == 2
        assert isinstance(curated, WebSearchResults)
        assert curated.results[0].url == "https://Example.COM/page#frag"
        assert curated.results[1].url == "https://example.com/other"
        assert call_count == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_pagination_fetches_multiple_pages(self, google_env: None) -> None:
        pages: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            start = int(request.url.params.get("start", "1"))
            num = int(request.url.params.get("num", "10"))
            pages.append(start)
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "link": f"https://example.com/{start + index}",
                            "title": f"Page {start} #{index}",
                            "snippet": "snippet",
                        }
                        for index in range(num)
                    ],
                },
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(http_client=client)
            _raw, curated = await engine.search(
                GoogleSearchRequest(query="pages", fetch_size=15),
                timeout=30,
            )

        from unique_search_proxy_core.schema import WebSearchResults

        assert pages == [1, 11]
        assert len(curated) == 15
        assert isinstance(curated, WebSearchResults)
        assert len(_raw.pages) == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call_overrides_config_parameters(self, google_env: None) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["gl"] = request.url.params.get("gl", "")
            return httpx.Response(200, json={"items": [_minimal_google_item()]})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(
                GoogleConfig(gl="us"),
                http_client=client,
            )
            await engine.search(
                GoogleSearchRequest(query="hello", gl="de"),
                timeout=30,
            )

        assert captured["gl"] == "de"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call_search_engine_id_overrides_env_cx(
        self, google_env: None
    ) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["cx"] = request.url.params.get("cx", "")
            return httpx.Response(200, json={"items": [_minimal_google_item()]})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(http_client=client)
            await engine.search(
                GoogleSearchRequest(query="hello", search_engine_id="call-cx"),
                timeout=30,
            )

        assert captured["cx"] == "call-cx"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call_search_engine_id_without_env_cx(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reset_google_search_settings_for_tests()
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID", raising=False)
        monkeypatch.setenv(
            "GOOGLE_SEARCH_API_ENDPOINT",
            "https://customsearch.googleapis.com/customsearch/v1",
        )

        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["cx"] = request.url.params.get("cx", "")
            return httpx.Response(200, json={"items": [_minimal_google_item()]})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(http_client=client)
            await engine.search(
                GoogleSearchRequest(
                    query="hello",
                    search_engine_id="call-only-cx",
                ),
                timeout=30,
            )

        assert captured["cx"] == "call-only-cx"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_empty_items_raises_empty_search_results(
        self, google_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"items": []})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(GoogleConfig(), http_client=client)
            with pytest.raises(EmptySearchResultsError, match="no results"):
                await engine.search(GoogleSearchRequest(query="hello"), timeout=30)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_missing_items_raises_empty_search_results(
        self, google_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"searchInformation": {"totalResults": "0"}}
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(GoogleConfig(), http_client=client)
            with pytest.raises(EmptySearchResultsError, match="no results"):
                await engine.search(GoogleSearchRequest(query="hello"), timeout=30)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_items_without_valid_url_scheme_are_included(
        self, google_env: None
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"items": [{"link": "not-a-url", "title": "Bad"}]},
            )

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(GoogleConfig(), http_client=client)
            _raw, curated = await engine.search(
                GoogleSearchRequest(query="hello"),
                timeout=30,
            )

        from unique_search_proxy_core.schema import WebSearchResults

        assert len(curated) == 1
        assert isinstance(curated, WebSearchResults)
        assert curated.results[0].url == "not-a-url"
        assert curated.results[0].title == "Bad"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_stops_when_subsequent_page_is_empty(self, google_env: None) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            start = int(request.url.params.get("start", "1"))
            if start == 1:
                return httpx.Response(200, json={"items": [_minimal_google_item()]})
            return httpx.Response(200, json={"items": []})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(http_client=client)
            _raw, curated = await engine.search(
                GoogleSearchRequest(query="hello", fetch_size=20),
                timeout=30,
            )

        assert call_count == 2
        assert len(curated) == 1

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_missing_credentials_raises_503(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reset_google_search_settings_for_tests()
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "")

        engine = GoogleSearchService(GoogleConfig())
        with pytest.raises(EngineNotConfiguredError):
            await engine.search(GoogleSearchRequest(query="hello"), timeout=30)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_upstream_error_on_non_success(self, google_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": {"message": "backend"}})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(GoogleConfig(), http_client=client)
            with pytest.raises(UpstreamError, match="500"):
                await engine.search(GoogleSearchRequest(query="fail"), timeout=30)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_rate_limited_raises_429(self, google_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, headers={"Retry-After": "12"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(GoogleConfig(), http_client=client)
            with pytest.raises(RateLimitedError) as exc_info:
                await engine.search(GoogleSearchRequest(query="slow"), timeout=30)
            assert exc_info.value.retry_after_seconds == 12

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_timeout_maps_to_upstream_timeout(self, google_env: None) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            engine = GoogleSearchService(GoogleConfig(), http_client=client)
            with pytest.raises(UpstreamTimeoutError):
                await engine.search(GoogleSearchRequest(query="slow"), timeout=1)


class TestGoogleSearchEndpoint:
    @pytest.mark.ai
    def test_not_configured_returns_503(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        reset_google_search_settings_for_tests()
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "")
        resp = client.post("/v1/search", json=_search_body())
        assert resp.status_code == 503
        assert (
            resp.json()["error"]["code"] == ProxyErrorCode.ENGINE_NOT_CONFIGURED.value
        )

    @pytest.mark.ai
    def test_validation_error_returns_422(self, google_client: TestClient) -> None:
        resp = google_client.post(
            "/v1/search",
            json={"engine": "google", "query": "", "fetchSize": 10, "timeout": 30},
        )
        assert resp.status_code == 422

    @pytest.mark.ai
    def test_search_success_returns_raw_and_curated(
        self,
        google_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def mock_search(
            self: GoogleSearchService,
            call: GoogleSearchRequest,
            *,
            timeout: int,
        ) -> tuple[dict[str, Any], list]:
            from unique_search_proxy_core.schema import WebSearchResult

            payload = _google_items_payload()
            results = [
                WebSearchResult(
                    url="https://example.com/page",
                    title="Example",
                    snippet="An example snippet",
                ),
            ]
            return payload, results

        monkeypatch.setattr(GoogleSearchService, "search", mock_search)
        resp = google_client.post(
            "/v1/search",
            json=_search_body(query="hello", fetchSize=5),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "hello"

    @pytest.mark.ai
    def test_call_sends_provider_params_from_payload(
        self,
        google_env: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["dateRestrict"] = request.url.params.get("dateRestrict", "")
            captured["gl"] = request.url.params.get("gl", "")
            return httpx.Response(200, json=_google_items_payload())

        pool_transport = httpx.MockTransport(handler)

        from unique_search_proxy_client.web.core.client.service import HttpClientPool

        async def mock_create_pool() -> HttpClientPool:
            client = httpx.AsyncClient(transport=pool_transport)
            return HttpClientPool(client=client)

        monkeypatch.setattr(
            "unique_search_proxy_client.web.app.create_http_client_pool",
            mock_create_pool,
        )
        with TestClient(create_app()) as client:
            resp = client.post(
                "/v1/search",
                json=_search_body(dateRestrict="d7", gl="de"),
            )

        assert resp.status_code == 200
        assert captured["dateRestrict"] == "d7"
        assert captured["gl"] == "de"

    @pytest.mark.ai
    def test_upstream_error_returns_502(
        self,
        google_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def mock_search(
            self: GoogleSearchService,
            call: GoogleSearchRequest,
            *,
            timeout: int,
        ) -> tuple[Any, list]:
            raise UpstreamError("Google failed", engine="google")

        monkeypatch.setattr(GoogleSearchService, "search", mock_search)
        resp = google_client.post("/v1/search", json=_search_body())
        assert resp.status_code == 502

    @pytest.mark.ai
    def test_timeout_returns_504(
        self,
        google_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def mock_search(
            self: GoogleSearchService,
            call: GoogleSearchRequest,
            *,
            timeout: int,
        ) -> tuple[Any, list]:
            raise UpstreamTimeoutError("timed out", engine="google")

        monkeypatch.setattr(GoogleSearchService, "search", mock_search)
        resp = google_client.post(
            "/v1/search",
            json={**_search_body(), "timeout": 1},
        )
        assert resp.status_code == 504

    @pytest.mark.ai
    def test_end_to_end_with_mock_transport(
        self,
        google_env: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_google_items_payload())

        pool_transport = httpx.MockTransport(handler)

        from unique_search_proxy_client.web.core.client.service import HttpClientPool

        async def mock_create_pool() -> HttpClientPool:
            client = httpx.AsyncClient(transport=pool_transport)
            return HttpClientPool(client=client)

        monkeypatch.setattr(
            "unique_search_proxy_client.web.app.create_http_client_pool",
            mock_create_pool,
        )
        with TestClient(create_app()) as client:
            resp = client.post("/v1/search", json=_search_body())

        assert resp.status_code == 200
        assert len(resp.json()["curated"]) == 2
