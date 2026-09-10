import json

import pytest
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError

from unique_search_proxy_client.web.core.client.credentials import (
    SettingsProxyCredentials,
    UserMetadataProxyCredentials,
    resolver_from_settings,
)
from unique_search_proxy_client.web.core.client.service import (
    ProxiedRoute,
    build_route,
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


def _context(
    user_metadata: dict[str, object] | None = None,
    *,
    company_id: str = "company-a",
) -> RequestContext:
    return RequestContext(
        company_id=company_id,
        user_id="user-1",
        chat_id="chat-1",
        user_metadata=user_metadata or {},
    )


class TestHttpClientSettings:
    @pytest.mark.ai
    def test_defaults(self) -> None:
        settings = get_http_client_settings()
        assert settings.proxy_auth_mode == "none"
        assert settings.pool_timeout_seconds == 30.0
        assert settings.max_connections == 100
        assert settings.proxy_headers == {}
        assert settings.proxy_username_source == "settings"
        assert settings.proxy_username_metadata_field == "userName"
        assert settings.per_user_proxy_company_ids == []
        assert settings.http_client_cache_size == 128
        assert settings.proxy_password.get_secret_value() == ""

    @pytest.mark.ai
    def test_proxy_auth_mode_literal(self) -> None:
        mode: ProxyAuthMode = "username_password"
        settings = type(get_http_client_settings())(
            proxy_auth_mode=mode,
            proxy_username=LogSecretStr("proxy-user"),
        )
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
        assert settings.proxy_password.get_secret_value() == "proxy-pass"
        assert read_secret_headers(settings.proxy_headers) == headers

    @pytest.mark.ai
    def test_empty_password_is_the_default(self) -> None:
        settings = HttpClientSettings()
        assert settings.proxy_password.get_secret_value() == ""

    @pytest.mark.ai
    def test_loads_username_source_config_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HTTP_CLIENT_PROXY_USERNAME_SOURCE", "user_metadata")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_HOST", "proxy.example.com")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_PORT", "8080")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_USERNAME_METADATA_FIELD", "email")
        monkeypatch.setenv(
            "HTTP_CLIENT_PER_USER_PROXY_COMPANY_IDS",
            json.dumps(["company-a", "company-b"]),
        )
        monkeypatch.setenv("HTTP_CLIENT_HTTP_CLIENT_CACHE_SIZE", "8")
        settings = get_http_client_settings()

        assert settings.proxy_username_source == "user_metadata"
        assert settings.proxy_username_metadata_field == "email"
        assert settings.per_user_proxy_company_ids == ["company-a", "company-b"]
        assert settings.http_client_cache_size == 8

    @pytest.mark.ai
    def test_user_metadata_source_requires_proxy_host_and_port(self) -> None:
        with pytest.raises(ValueError, match="Proxy host and port"):
            HttpClientSettings(proxy_username_source="user_metadata")

    @pytest.mark.ai
    def test_settings_username_password_requires_username(self) -> None:
        with pytest.raises(ValueError, match="proxy_username is required"):
            HttpClientSettings(proxy_auth_mode="username_password")

    @pytest.mark.ai
    def test_build_route_puts_credentials_on_the_proxy_object(self) -> None:
        settings = HttpClientSettings(
            proxy_auth_mode="username_password",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username=LogSecretStr("technical"),
            proxy_password=LogSecretStr(""),
            proxy_headers={
                "X-Custom": LogSecretStr("value"),
            },
        )
        credentials = SettingsProxyCredentials(settings).resolve(_context())
        route = build_route(settings, credentials)

        assert isinstance(route, ProxiedRoute)
        assert route.headers == {"X-Custom": "value"}
        assert str(route.proxy.url) == "http://proxy.example.com:8080"
        assert route.proxy.auth == ("technical", "")

    @pytest.mark.ai
    def test_build_route_keeps_special_characters_out_of_the_url(self) -> None:
        from unique_search_proxy_client.web.core.client.credentials import (
            ProxyCredentials,
        )

        settings = HttpClientSettings(
            proxy_auth_mode="username_password",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username=LogSecretStr("ignored"),
        )
        route = build_route(
            settings,
            ProxyCredentials(username="user:with@special/chars", password=""),
        )

        assert isinstance(route, ProxiedRoute)
        assert str(route.proxy.url) == "http://proxy.example.com:8080"
        assert route.proxy.auth == ("user:with@special/chars", "")


class TestProxyCredentialResolvers:
    @pytest.mark.ai
    def test_settings_resolver_returns_anonymous_when_proxy_is_off(self) -> None:
        settings = HttpClientSettings(proxy_auth_mode="none")
        credentials = SettingsProxyCredentials(settings).resolve(_context())
        assert credentials.is_anonymous

    @pytest.mark.ai
    def test_user_metadata_resolver_reads_configured_field(self) -> None:
        settings = HttpClientSettings(
            proxy_username_source="user_metadata",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_password=LogSecretStr(""),
        )
        credentials = UserMetadataProxyCredentials(settings).resolve(
            _context({"userName": "u12345", "email": "a@b.com"}),
        )
        assert credentials.username == "u12345"
        assert credentials.password == ""

    @pytest.mark.ai
    def test_user_metadata_field_is_configurable(self) -> None:
        settings = HttpClientSettings(
            proxy_username_source="user_metadata",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username_metadata_field="email",
        )
        credentials = UserMetadataProxyCredentials(settings).resolve(
            _context({"userName": "u12345", "email": "a@b.com"}),
        )
        assert credentials.username == "a@b.com"

    @pytest.mark.ai
    def test_user_metadata_fails_closed_without_identity(self) -> None:
        settings = HttpClientSettings(
            proxy_username_source="user_metadata",
            proxy_host="proxy.example.com",
            proxy_port=8080,
        )
        with pytest.raises(ValidationProxyError, match="userName"):
            UserMetadataProxyCredentials(settings).resolve(_context({}))

    @pytest.mark.ai
    def test_allowlist_falls_back_to_settings_credentials(self) -> None:
        settings = HttpClientSettings(
            proxy_auth_mode="username_password",
            proxy_username_source="user_metadata",
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username=LogSecretStr("technical"),
            proxy_password=LogSecretStr("secret"),
            per_user_proxy_company_ids=["company-a"],
        )
        credentials = UserMetadataProxyCredentials(settings).resolve(
            _context({"userName": "u12345"}, company_id="company-z"),
        )
        assert credentials.username == "technical"
        assert credentials.password == "secret"

    @pytest.mark.ai
    def test_resolver_from_settings_picks_user_metadata(self) -> None:
        settings = HttpClientSettings(
            proxy_username_source="user_metadata",
            proxy_host="proxy.example.com",
            proxy_port=8080,
        )
        resolver = resolver_from_settings(settings)
        assert isinstance(resolver, UserMetadataProxyCredentials)


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

    @pytest.mark.ai
    def test_password_is_masked_in_startup_report(self) -> None:
        settings = HttpClientSettings(proxy_password=LogSecretStr("secret"))
        assert "secret" not in _format_settings_value(settings.proxy_password)
