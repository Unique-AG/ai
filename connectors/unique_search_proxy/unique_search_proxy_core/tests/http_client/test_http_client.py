"""Tests for the shared HTTP client in unique_search_proxy_core."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError
from unique_search_proxy_core.http_client import (
    HttpClientRegistry,
    ProxiedRoute,
    ProxySettings,
    SettingsProxyCredentials,
    UserMetadataProxyCredentials,
    build_route,
    resolver_from_settings,
)


def _settings(**overrides: object) -> ProxySettings:
    defaults: dict[str, object] = {
        "proxy_auth_mode": "username_password",
        "proxy_host": "proxy.example.com",
        "proxy_port": 8080,
        "proxy_username": SecretStr("technical"),
        "proxy_password": SecretStr(""),
        "proxy_username_source": "user_metadata",
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
        settings = _settings(proxy_username_source="settings")
        credentials = SettingsProxyCredentials(settings).resolve(_context())
        route = build_route(settings, credentials)

        assert isinstance(route, ProxiedRoute)
        assert str(route.proxy.url) == "http://proxy.example.com:8080"
        assert route.proxy.auth == ("technical", "")

    def test_user_metadata_resolver_fails_closed(self) -> None:
        with pytest.raises(ValidationProxyError):
            UserMetadataProxyCredentials(_settings()).resolve(
                RequestContext(
                    company_id="company-a",
                    user_id="u",
                    chat_id="c",
                    user_metadata={},
                ),
            )

    def test_resolver_from_settings_picks_metadata(self) -> None:
        assert isinstance(
            resolver_from_settings(_settings()),
            UserMetadataProxyCredentials,
        )

    async def test_registry_isolates_users(self) -> None:
        settings = _settings()
        registry = HttpClientRegistry(
            settings=settings,
            resolver=resolver_from_settings(settings),
        )
        try:
            first = await registry.client_for(_context("u1"))
            other = await registry.client_for(_context("u2"))
            assert first is not other
        finally:
            await registry.aclose()

    def test_registry_constructs_without_settings_username(self) -> None:
        settings = _settings(proxy_username=None)
        registry = HttpClientRegistry(
            settings=settings,
            resolver=resolver_from_settings(settings),
        )
        assert registry.size == 0
