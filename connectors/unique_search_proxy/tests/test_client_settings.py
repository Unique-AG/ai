import pytest

from unique_search_proxy.web.core.client.settings import (
    HttpClientSettingsForTests,
    ProxyAuthMode,
)


class TestHttpClientSettings:
    @pytest.mark.ai
    def test_defaults(self) -> None:
        settings = HttpClientSettingsForTests()
        assert settings.proxy_auth_mode == "none"
        assert settings.pool_timeout_seconds == 30.0
        assert settings.max_connections == 100

    @pytest.mark.ai
    def test_proxy_auth_mode_literal(self) -> None:
        mode: ProxyAuthMode = "username_password"
        settings = HttpClientSettingsForTests(proxy_auth_mode=mode)
        assert settings.proxy_auth_mode == "username_password"

    @pytest.mark.ai
    def test_loads_from_prefixed_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_CLIENT_PROXY_AUTH_MODE", "none")
        monkeypatch.setenv("HTTP_CLIENT_POOL_TIMEOUT_SECONDS", "45")
        monkeypatch.setenv("HTTP_CLIENT_MAX_CONNECTIONS", "50")
        settings = HttpClientSettingsForTests()
        assert settings.pool_timeout_seconds == 45.0
        assert settings.max_connections == 50
