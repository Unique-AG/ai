import json

import pytest

from unique_search_proxy_client.web.core.client.service import (
    build_per_user_async_client,
    build_proxy_config,
)
from unique_search_proxy_client.web.settings.client import (
    HttpClientSettings,
    ProxyAuthMode,
    get_http_client_settings,
)
from unique_search_proxy_client.web.settings.secret_str import (
    LogSecretStr,
    read_secret_headers,
)
from unique_search_proxy_client.web.startup_report import (
    _format_settings_value,
)


class TestHttpClientSettings:
    @pytest.mark.ai
    def test_defaults(self) -> None:
        settings = get_http_client_settings()
        assert settings.proxy_auth_mode == "none"
        assert settings.pool_timeout_seconds == 30.0
        assert settings.max_connections == 100
        assert settings.proxy_headers == {}
        assert settings.per_user_proxy_company_ids == []
        assert settings.per_user_proxy_password is None
        assert settings.per_user_proxy_client_cache_size == 128

    @pytest.mark.ai
    def test_proxy_auth_mode_literal(self) -> None:
        mode: ProxyAuthMode = "username_password"
        settings = get_http_client_settings()
        settings = type(settings)(proxy_auth_mode=mode)
        assert settings.proxy_auth_mode == "username_password"

    @pytest.mark.ai
    def test_loads_from_prefixed_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_CLIENT_PROXY_AUTH_MODE", "none")
        monkeypatch.setenv("HTTP_CLIENT_POOL_TIMEOUT_SECONDS", "45")
        monkeypatch.setenv("HTTP_CLIENT_MAX_CONNECTIONS", "50")
        settings = get_http_client_settings()
        assert settings.pool_timeout_seconds == 45.0
        assert settings.max_connections == 50

    @pytest.mark.ai
    def test_loads_per_user_proxy_configuration(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "HTTP_CLIENT_PER_USER_PROXY_COMPANY_IDS",
            '["company-1", "company-2"]',
        )
        monkeypatch.setenv("HTTP_CLIENT_PER_USER_PROXY_PASSWORD", "placeholder")
        monkeypatch.setenv("HTTP_CLIENT_PER_USER_PROXY_CLIENT_CACHE_SIZE", "64")

        settings = get_http_client_settings()

        assert settings.per_user_proxy_enabled_for("company-1")
        assert settings.per_user_proxy_password is not None
        assert settings.per_user_proxy_password.get_secret_value() == "placeholder"
        assert settings.per_user_proxy_client_cache_size == 64

    @pytest.mark.ai
    def test_loads_proxy_secrets_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        headers = {"Proxy-Authorization": "Basic abc123token"}
        monkeypatch.setenv("HTTP_CLIENT_PROXY_USERNAME", "proxy-user")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_PASSWORD", "proxy-pass")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_HEADERS", json.dumps(headers))
        settings = get_http_client_settings()

        assert settings.proxy_username is not None
        assert settings.proxy_username.get_secret_value() == "proxy-user"
        assert settings.proxy_password is not None
        assert settings.proxy_password.get_secret_value() == "proxy-pass"
        assert read_secret_headers(settings.proxy_headers) == headers

    @pytest.mark.ai
    def test_build_proxy_config_unwraps_secret_headers(self) -> None:
        settings = HttpClientSettings(
            proxy_auth_mode="ssl_tls",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_ssl_cert_path="/tmp/cert.pem",
            proxy_headers={
                "Proxy-Authorization": LogSecretStr("Bearer secret-token"),
            },
        )
        config = build_proxy_config(settings)
        assert config.headers == {"Proxy-Authorization": "Bearer secret-token"}

    @pytest.mark.ai
    def test_build_per_user_client_accepts_empty_placeholder_password(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, object] = {}

        class FakeProxy:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

        class FakeClient:
            def __init__(self, **_kwargs: object) -> None:
                pass

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.client.service.httpx.Proxy",
            FakeProxy,
        )
        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.client.service.AsyncClient",
            FakeClient,
        )
        settings = HttpClientSettings(
            proxy_host="proxy.example.com",
            proxy_port=8080,
            per_user_proxy_password=LogSecretStr(""),
        )

        build_per_user_async_client("client-user", settings=settings)

        assert captured["url"] == "http://proxy.example.com:8080"
        assert captured["auth"] == ("client-user", "")


class TestHttpClientSecretFormatting:
    @pytest.mark.ai
    def test_format_settings_value_masks_secret_headers(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import unique_search_proxy_client.web.settings.secret_str as secret_str_module
        from unique_search_proxy_client.web.settings.secret_str import (
            StartupLogSettings,
        )

        monkeypatch.setattr(
            secret_str_module,
            "startup_log_settings",
            StartupLogSettings(secret_suffix_len=3),
        )
        rendered = _format_settings_value(
            {"Proxy-Authorization": LogSecretStr("Bearer secret-token")},
        )
        assert rendered == "{'Proxy-Authorization': **********}"

    @pytest.mark.ai
    def test_read_secret_headers(self) -> None:
        headers = {
            "Authorization": LogSecretStr("Bearer abc"),
            "X-Custom": LogSecretStr("value"),
        }
        assert read_secret_headers(headers) == {
            "Authorization": "Bearer abc",
            "X-Custom": "value",
        }
