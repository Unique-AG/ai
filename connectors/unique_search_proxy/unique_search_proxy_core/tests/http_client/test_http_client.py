"""Tests for the shared HTTP client in unique_search_proxy_core."""

from __future__ import annotations

import httpx
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
from unique_search_proxy_core.url_safety import UrlSafetySettings


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


def _set_url_safety_enabled(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enabled: bool,
) -> None:
    import unique_search_proxy_core.http_client.client as client_module

    monkeypatch.setattr(
        client_module,
        "url_safety_settings",
        UrlSafetySettings(enabled=enabled),
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

    def test_registry_rejects_disabled_url_safety_without_proxy(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)

        with pytest.raises(
            ValueError,
            match="no usable corporate proxy endpoint is configured",
        ) as exc_info:
            settings = ProxySettings()
            HttpClientRegistry(
                settings=settings,
                resolver=resolver_from_settings(settings),
            )

        message = str(exc_info.value)
        assert "URL_SAFETY_ENABLED=true" in message
        assert "configure an authenticated corporate proxy for all egress" in message

    @pytest.mark.parametrize("proxy_port", [0, 65536])
    def test_registry_rejects_invalid_proxy_port_when_url_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        proxy_port: int,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        settings = _settings(proxy_port=proxy_port)

        with pytest.raises(ValueError, match="proxy_port must be between 1 and 65535"):
            HttpClientRegistry(
                settings=settings,
                resolver=resolver_from_settings(settings),
            )

    def test_registry_rejects_direct_route_when_url_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        settings = ProxySettings(
            proxy_host="proxy.example.com",
            proxy_port=8080,
        )

        with pytest.raises(ValueError, match="do not route every request through"):
            HttpClientRegistry(
                settings=settings,
                resolver=resolver_from_settings(settings),
            )

    def test_registry_accepts_authenticated_proxy_when_url_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        settings = _settings(proxy_username_source="settings")

        registry = HttpClientRegistry(
            settings=settings,
            resolver=resolver_from_settings(settings),
        )

        assert registry.size == 0

    def test_registry_rejects_partial_tenant_proxy_when_url_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        settings = _settings(
            proxy_auth_mode="none",
            per_user_proxy_company_ids=["company-a"],
        )

        with pytest.raises(ValueError, match="do not route every request through"):
            HttpClientRegistry(
                settings=settings,
                resolver=resolver_from_settings(settings),
            )

    def test_registry_accepts_global_user_proxy_when_url_safety_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        settings = _settings(proxy_username=None)

        registry = HttpClientRegistry(
            settings=settings,
            resolver=resolver_from_settings(settings),
        )

        assert registry.size == 0

    def test_registry_requires_certificate_for_disabled_url_safety_with_mtls(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        settings = _settings(
            proxy_auth_mode="ssl_tls",
            proxy_ssl_cert_path=None,
        )

        with pytest.raises(
            ValueError,
            match="SSL/TLS proxy authentication is missing proxy_ssl_cert_path",
        ):
            HttpClientRegistry(
                settings=settings,
                resolver=resolver_from_settings(settings),
            )

    async def test_fixed_registry_bypasses_egress_validation(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _set_url_safety_enabled(monkeypatch, enabled=False)
        registry = HttpClientRegistry.fixed(httpx.AsyncClient())

        try:
            assert registry.size == 1
        finally:
            await registry.aclose()
