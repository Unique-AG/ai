"""Tests for the shared HTTP client in unique_search_proxy_core."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError
from unique_search_proxy_core.http_client import (
    DirectRoute,
    HttpClientRegistry,
    ProxiedRoute,
    ProxySettings,
    build_route,
    resolve_identity,
)

_UID_HEADER = "X-Unique-End-User-Id"


def _settings(**overrides: object) -> ProxySettings:
    defaults: dict[str, object] = {
        "proxy_auth_mode": "username_password",
        "proxy_host": "proxy.example.com",
        "proxy_port": 8080,
        "proxy_username": SecretStr("technical"),
        "proxy_password": SecretStr(""),
        "proxy_user_id_header": _UID_HEADER,
    }
    defaults.update(overrides)
    return ProxySettings(**defaults)  # type: ignore[arg-type]


def _context(
    username: str = "u1",
    *,
    company_id: str = "company-a",
) -> RequestContext:
    return RequestContext(
        company_id=company_id,
        user_id="user-1",
        chat_id="chat-1",
        user_metadata={"userName": username},
    )


@pytest.mark.ai
class TestCoreHttpClient:
    def test_build_route_keeps_credentials_off_the_url(self) -> None:
        settings = _settings(proxy_user_id_header=None)
        route = build_route(settings, resolve_identity(settings, _context()))

        assert isinstance(route, ProxiedRoute)
        assert str(route.proxy.url) == "http://proxy.example.com:8080"
        assert route.proxy.auth == ("technical", "")

    def test_service_credentials_and_uid_travel_together(self) -> None:
        settings = _settings()
        route = build_route(settings, resolve_identity(settings, _context("u1234567")))

        assert isinstance(route, ProxiedRoute)
        assert route.proxy.auth == ("technical", "")
        assert route.proxy.headers[_UID_HEADER] == "u1234567"

    def test_missing_uid_fails_closed(self) -> None:
        with pytest.raises(ValidationProxyError):
            resolve_identity(
                _settings(),
                RequestContext(
                    company_id="company-a",
                    user_id="u",
                    chat_id="c",
                    user_metadata={},
                ),
            )

    def test_no_proxy_host_yields_direct_egress(self) -> None:
        settings = ProxySettings()
        route = build_route(settings, resolve_identity(settings, _context()))

        assert isinstance(route, DirectRoute)

    async def test_registry_isolates_users(self) -> None:
        registry = HttpClientRegistry(settings=_settings())
        try:
            first = await registry.client_for(_context("u1"))
            other = await registry.client_for(_context("u2"))
            assert first is not other
        finally:
            await registry.aclose()

    def test_registry_constructs_without_opening_clients(self) -> None:
        registry = HttpClientRegistry(settings=_settings())
        assert registry.size == 0
