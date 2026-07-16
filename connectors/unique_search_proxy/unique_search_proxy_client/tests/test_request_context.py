"""Tests for request context middleware and logging."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.context import (
    LOCAL_REQUEST_CONTEXT,
    RequestContext,
)
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.settings.app import AppSettings


def _context_headers(
    *,
    company_id: str = "company-1",
    user_id: str = "user-1",
    chat_id: str = "chat-1",
) -> dict[str, str]:
    return RequestContext(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
    ).to_headers()


@pytest.fixture
def enforcement_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "unique_search_proxy_client.web.middleware.context.app_settings",
        AppSettings(require_context_headers=True),
    )
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def relaxed_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "unique_search_proxy_client.web.middleware.context.app_settings",
        AppSettings(require_context_headers=False),
    )
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.mark.ai
class TestRequestContextMiddleware:
    def test_missing_headers_rejected_when_enforcement_enabled(
        self,
        enforcement_client: TestClient,
    ) -> None:
        response = enforcement_client.post(
            "/v1/search",
            json={"engine": "google", "query": "test", "fetchSize": 1},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == ProxyErrorCode.VALIDATION_ERROR.value
        assert "Missing required context headers" in body["error"]["message"]

    def test_present_headers_accepted_when_enforcement_enabled(
        self,
        enforcement_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-cx")

        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResult,
            WebSearchResults,
        )
        from unique_search_proxy_core.search_engines.google.schema import (
            GoogleSearchRequest,
        )

        async def fake_search(
            self: object,
            request: GoogleSearchRequest,
        ) -> tuple[SearchEngineRaw, WebSearchResults]:
            return SearchEngineRaw(pages=[]), WebSearchResults(
                results=[
                    WebSearchResult(url="https://example.com", title="t", snippet="s"),
                ],
            )

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.google.service.GoogleSearchService.search",
            fake_search,
        )

        response = enforcement_client.post(
            "/v1/search",
            headers=_context_headers(),
            json={"engine": "google", "query": "test", "fetchSize": 1},
        )
        assert response.status_code == 200
        assert response.json()["engine"] == "google"

    def test_missing_headers_accepted_when_enforcement_disabled(
        self,
        relaxed_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-cx")

        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResult,
            WebSearchResults,
        )
        from unique_search_proxy_core.search_engines.google.schema import (
            GoogleSearchRequest,
        )

        async def fake_search(
            self: object,
            request: GoogleSearchRequest,
        ) -> tuple[SearchEngineRaw, WebSearchResults]:
            return SearchEngineRaw(pages=[]), WebSearchResults(
                results=[
                    WebSearchResult(url="https://example.com", title="t", snippet="s"),
                ],
            )

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.google.service.GoogleSearchService.search",
            fake_search,
        )

        response = relaxed_client.post(
            "/v1/search",
            json={"engine": "google", "query": "test", "fetchSize": 1},
        )
        assert response.status_code == 200

    def test_local_default_headers_accepted_when_enforcement_enabled(
        self,
        enforcement_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID", "test-cx")

        from unique_search_proxy_core.schema import (
            SearchEngineRaw,
            WebSearchResult,
            WebSearchResults,
        )
        from unique_search_proxy_core.search_engines.google.schema import (
            GoogleSearchRequest,
        )

        async def fake_search(
            self: object,
            request: GoogleSearchRequest,
        ) -> tuple[SearchEngineRaw, WebSearchResults]:
            return SearchEngineRaw(pages=[]), WebSearchResults(
                results=[
                    WebSearchResult(url="https://example.com", title="t", snippet="s"),
                ],
            )

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.search_engines.google.service.GoogleSearchService.search",
            fake_search,
        )

        response = enforcement_client.post(
            "/v1/search",
            headers=LOCAL_REQUEST_CONTEXT.to_headers(),
            json={"engine": "google", "query": "test", "fetchSize": 1},
        )
        assert response.status_code == 200
