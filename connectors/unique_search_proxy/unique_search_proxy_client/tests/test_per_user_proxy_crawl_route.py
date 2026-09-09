"""Crawl-route behaviour when a tenant is gated for per-user proxy authentication."""

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
from unique_search_proxy_client.web.core.client.per_user import PerUserProxyClientCache
from unique_search_proxy_client.web.core.client.service import HttpClientPool
from unique_search_proxy_client.web.settings.client import HttpClientSettings
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_GATED_COMPANY = "company-a"
_UNGATED_COMPANY = "company-z"
_HTML_PAGE = "<html><head><title>T</title></head><body><h1>Hello</h1></body></html>"


@dataclass
class _Egress:
    """Records which client each outbound request used."""

    shared: list[httpx.Request] = field(default_factory=list)
    per_user: list[tuple[str, httpx.Request]] = field(default_factory=list)

    @property
    def per_user_names(self) -> list[str]:
        return [username for username, _request in self.per_user]


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
    def shared_handler(request: httpx.Request) -> httpx.Response:
        egress.shared.append(request)
        return _page_response(request)

    async def mock_create_pool() -> HttpClientPool:
        return HttpClientPool(
            client=httpx.AsyncClient(transport=httpx.MockTransport(shared_handler)),
        )

    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_http_client_pool",
        mock_create_pool,
    )

    def fake_per_user_client(
        proxy_username: str,
        *,
        settings: HttpClientSettings | None = None,
        timeout: float | None = None,
    ) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            egress.per_user.append((proxy_username, request))
            return _page_response(request)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.client.per_user.build_per_user_async_client",
        fake_per_user_client,
    )

    gated_settings = HttpClientSettings(
        proxy_host="proxy.example.com",
        proxy_port=8080,
        per_user_proxy_company_ids=[_GATED_COMPANY],
        per_user_proxy_password=LogSecretStr(""),
    )
    monkeypatch.setattr(
        "unique_search_proxy_client.web.app.create_per_user_proxy_client_cache",
        lambda: PerUserProxyClientCache(gated_settings),
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
        user_metadata=user_metadata,
    ).to_headers()


def _crawl(
    client: TestClient,
    *,
    company_id: str,
    user_metadata: dict[str, Any] | None = None,
    crawler: str = CrawlerType.BASIC.value,
) -> httpx.Response:
    return client.post(
        "/v1/crawl",
        json={
            "urls": ["https://example.com/article"],
            "crawler": crawler,
            "timeout": 10,
            "contentTypes": {"html": True},
        },
        headers=_headers(company_id, user_metadata),
    )


@pytest.mark.ai
def test_gated_company_fetches_as_the_end_user(
    client: TestClient,
    egress: _Egress,
) -> None:
    response = _crawl(
        client,
        company_id=_GATED_COMPANY,
        user_metadata={"userName": "u12345"},
    )

    assert response.status_code == 200
    assert egress.per_user_names == ["u12345"]
    assert egress.shared == []


@pytest.mark.ai
def test_ungated_company_keeps_using_the_shared_client(
    client: TestClient,
    egress: _Egress,
) -> None:
    """Per-tenant gating: everyone else must be unaffected by this feature."""
    response = _crawl(
        client,
        company_id=_UNGATED_COMPANY,
        user_metadata={"userName": "u12345"},
    )

    assert response.status_code == 200
    assert egress.per_user == []
    assert len(egress.shared) == 1


@pytest.mark.ai
def test_gated_company_without_identity_fails_closed(
    client: TestClient,
    egress: _Egress,
) -> None:
    """Refuse the fetch rather than silently using the shared technical account."""
    response = _crawl(client, company_id=_GATED_COMPANY, user_metadata=None)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == ProxyErrorCode.VALIDATION_ERROR.value
    assert egress.per_user == []
    assert egress.shared == []


@pytest.mark.ai
def test_gated_company_rejects_crawlers_that_cannot_carry_the_identity(
    client: TestClient,
    egress: _Egress,
) -> None:
    response = _crawl(
        client,
        company_id=_GATED_COMPANY,
        user_metadata={"userName": "u12345"},
        crawler=CrawlerType.JINA.value,
    )

    assert response.status_code == 400
    assert "Basic crawler" in response.json()["error"]["message"]
    assert egress.per_user == []
    assert egress.shared == []


@pytest.mark.ai
def test_redirect_probe_uses_the_same_identity_as_the_fetch(
    client: TestClient,
    egress: _Egress,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The probe must traverse the proxy as the user, or it may see another page."""
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
    methods = {request.method for _username, request in egress.per_user}
    assert methods == {"HEAD", "GET"}
    assert set(egress.per_user_names) == {"u12345"}
    assert egress.shared == []


@pytest.mark.ai
def test_search_stays_on_the_shared_technical_account(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search-provider API calls are explicitly out of scope for per-user identity."""
    captured: list[httpx.AsyncClient | None] = []
    real_factory = __import__(
        "unique_search_proxy_client.web.api.v1.search",
        fromlist=["get_search_engine_service"],
    ).get_search_engine_service

    def capturing_factory(*args: Any, **kwargs: Any) -> Any:
        captured.append(kwargs.get("http_client"))
        return real_factory(*args, **kwargs)

    monkeypatch.setattr(
        "unique_search_proxy_client.web.api.v1.search.get_search_engine_service",
        capturing_factory,
    )

    client.post(
        "/v1/search",
        json={"query": "unique ai", "engine": "google", "timeout": 10},
        headers=_headers(_GATED_COMPANY, {"userName": "u12345"}),
    )

    assert captured, "expected the search route to build an engine"
    pool = client.app.state.http_client_pool  # type: ignore[attr-defined]
    assert captured[0] is pool.client
