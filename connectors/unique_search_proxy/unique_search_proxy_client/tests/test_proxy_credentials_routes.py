"""Search and crawl routes resolve egress through the credential-keyed registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.schema import ProxyErrorCode

from unique_search_proxy_client.web.app import create_app
from unique_search_proxy_client.web.core.client.service import (
    HttpClientRegistry,
)
from unique_search_proxy_client.web.settings.client import HttpClientSettings
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_GATED_COMPANY = "company-a"
_UNGATED_COMPANY = "company-z"
_HTML_PAGE = "<html><head><title>T</title></head><body><h1>Hello</h1></body></html>"


@dataclass
class _Egress:
    """Records which proxy username each outbound request used."""

    by_username: list[tuple[str, httpx.Request]] = field(default_factory=list)

    @property
    def usernames(self) -> list[str]:
        return [username for username, _request in self.by_username]


def _page_response(request: httpx.Request) -> httpx.Response:
    if request.method == "HEAD":
        return httpx.Response(200)
    return httpx.Response(
        200,
        text=_HTML_PAGE,
        headers={"content-type": "text/html; charset=utf-8"},
    )


@pytest.fixture
def egress() -> _Egress:
    return _Egress()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    egress: _Egress,
) -> Generator[TestClient, Any, None]:
    gated_settings = HttpClientSettings(
        proxy_auth_mode="username_password",
        proxy_host="proxy.example.com",
        proxy_port=8080,
        proxy_username=LogSecretStr("technical"),
        proxy_password=LogSecretStr(""),
        proxy_username_source="user_metadata",
        per_user_proxy_company_ids=[_GATED_COMPANY],
    )

    def tracking_build(
        settings: HttpClientSettings,
        credentials: Any,
        *,
        timeout: float,
    ) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            egress.by_username.append((credentials.username, request))
            return _page_response(request)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.client.service.build_async_client",
        tracking_build,
    )

    async def create_registry() -> HttpClientRegistry:
        from unique_search_proxy_client.web.core.client.credentials import (
            resolver_from_settings,
        )

        return HttpClientRegistry(
            settings=gated_settings,
            resolver=resolver_from_settings(gated_settings),
        )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_registry",
        create_registry,
    )

    with TestClient(create_app()) as test_client:
        yield test_client


def _headers(
    company_id: str,
    user_metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    return RequestContext(
        company_id=company_id,
        user_id="user-1",
        chat_id="chat-1",
        user_metadata=user_metadata or {},
    ).to_headers()


def _crawl(
    client: TestClient,
    *,
    company_id: str,
    user_metadata: dict[str, Any] | None = None,
) -> httpx.Response:
    return client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article"],
            "crawler": CrawlerType.BASIC.value,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
        headers=_headers(company_id, user_metadata),
    )


@pytest.mark.ai
def test_gated_company_crawls_as_the_end_user(
    client: TestClient,
    egress: _Egress,
) -> None:
    response = _crawl(
        client,
        company_id=_GATED_COMPANY,
        user_metadata={"userName": "u12345"},
    )

    assert response.status_code == 200
    assert set(egress.usernames) == {"u12345"}


@pytest.mark.ai
def test_ungated_company_uses_settings_credentials(
    client: TestClient,
    egress: _Egress,
) -> None:
    response = _crawl(
        client,
        company_id=_UNGATED_COMPANY,
        user_metadata={"userName": "u12345"},
    )

    assert response.status_code == 200
    assert set(egress.usernames) == {"technical"}


@pytest.mark.ai
def test_gated_company_without_identity_fails_closed(
    client: TestClient,
    egress: _Egress,
) -> None:
    response = _crawl(client, company_id=_GATED_COMPANY, user_metadata={})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == ProxyErrorCode.VALIDATION_ERROR.value
    assert egress.by_username == []


@pytest.mark.ai
def test_redirect_probe_and_fetch_share_identity(
    client: TestClient,
    egress: _Egress,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import unique_search_proxy_core.url_safety.service as service_module

    monkeypatch.setattr(
        service_module,
        "url_safety_settings",
        service_module.url_safety_settings.model_copy(
            update={"resolve_redirects": True},
        ),
    )

    response = _crawl(
        client,
        company_id=_GATED_COMPANY,
        user_metadata={"userName": "u12345"},
    )

    assert response.status_code == 200
    methods = {request.method for _username, request in egress.by_username}
    assert methods == {"HEAD", "GET"}
    assert set(egress.usernames) == {"u12345"}


@pytest.mark.ai
def test_search_also_uses_the_end_user_identity(
    client: TestClient,
    egress: _Egress,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unique_search_proxy_core.schema import WebSearchResult, WebSearchResults

    class _FakeEngine:
        async def search(self, body: Any) -> tuple[dict[str, Any], WebSearchResults]:
            return {}, WebSearchResults(
                results=[
                    WebSearchResult(
                        title="t",
                        url="https://example.com",
                        snippet="s",
                    )
                ],
            )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.api.v1.search.get_search_engine_service",
        lambda *args, **kwargs: _FakeEngine(),
    )

    # Force the search route to actually open an egress client before the fake engine.
    captured: list[httpx.AsyncClient] = []
    real_client_for = HttpClientRegistry.client_for

    async def capturing_client_for(self: HttpClientRegistry, context: RequestContext):
        client = await real_client_for(self, context)
        captured.append(client)
        # Touch the client so tracking_build records an egress call.
        await client.get("https://example.com/search-probe")
        return client

    monkeypatch.setattr(HttpClientRegistry, "client_for", capturing_client_for)

    response = client.post(
        "/v1/search",
        json={"query": "unique ai", "engine": "google", "timeout": 10},
        headers=_headers(_GATED_COMPANY, {"userName": "u12345"}),
    )

    assert response.status_code == 200
    assert captured
    assert "u12345" in egress.usernames
