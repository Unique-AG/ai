import json

import pytest
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError

from unique_search_proxy_client.web.core.client.credentials import (
    ProxyIdentity,
    resolve_identity,
)
from unique_search_proxy_client.web.core.client.service import (
    DirectRoute,
    ProxiedRoute,
    build_async_client,
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

_UID_HEADER = "X-Unique-End-User-Id"


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


def _proxy_settings(**overrides: object) -> HttpClientSettings:
    defaults: dict[str, object] = {
        "proxy_auth_mode": "username_password",
        "proxy_host": "proxy.example.com",
        "proxy_port": 8080,
        "proxy_username": LogSecretStr("technical"),
        "proxy_password": LogSecretStr("secret"),
    }
    defaults.update(overrides)
    return HttpClientSettings(**defaults)  # type: ignore[arg-type]


class TestHttpClientSettings:
    @pytest.mark.ai
    def test_defaults(self) -> None:
        settings = get_http_client_settings()
        assert settings.proxy_auth_mode == "none"
        assert settings.pool_timeout_seconds == 30.0
        assert settings.max_connections == 100
        assert settings.proxy_headers == {}
        assert settings.proxy_user_id_header is None
        assert settings.proxy_user_id_metadata_field == "userName"
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
        headers = {"X-Tenant": "acme"}
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
    def test_loads_user_id_header_config_from_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("HTTP_CLIENT_PROXY_USER_ID_HEADER", _UID_HEADER)
        monkeypatch.setenv("HTTP_CLIENT_PROXY_HOST", "proxy.example.com")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_PORT", "8080")
        monkeypatch.setenv("HTTP_CLIENT_PROXY_USER_ID_METADATA_FIELD", "email")
        monkeypatch.setenv("HTTP_CLIENT_HTTP_CLIENT_CACHE_SIZE", "8")
        settings = get_http_client_settings()

        assert settings.proxy_user_id_header == _UID_HEADER
        assert settings.proxy_user_id_metadata_field == "email"
        assert settings.http_client_cache_size == 8

    @pytest.mark.ai
    def test_user_id_header_requires_proxy_host_and_port(self) -> None:
        with pytest.raises(ValueError, match="proxy_host and proxy_port"):
            HttpClientSettings(proxy_user_id_header=_UID_HEADER)

    @pytest.mark.ai
    def test_proxy_host_and_port_must_be_set_together(self) -> None:
        with pytest.raises(ValueError, match="must be set together"):
            HttpClientSettings(proxy_host="proxy.example.com")

    @pytest.mark.ai
    def test_username_password_requires_username(self) -> None:
        with pytest.raises(ValueError, match="proxy_username is required"):
            HttpClientSettings(proxy_auth_mode="username_password")

    @pytest.mark.ai
    def test_ssl_tls_requires_cert_path(self) -> None:
        with pytest.raises(ValueError, match="proxy_ssl_cert_path is required"):
            HttpClientSettings(proxy_auth_mode="ssl_tls")

    @pytest.mark.ai
    @pytest.mark.parametrize(
        "removed",
        [
            "HTTP_CLIENT_PROXY_USERNAME_SOURCE",
            "HTTP_CLIENT_PROXY_USERNAME_METADATA_FIELD",
            "HTTP_CLIENT_PER_USER_PROXY_COMPANY_IDS",
        ],
    )
    def test_retired_env_vars_fail_loudly(
        self,
        monkeypatch: pytest.MonkeyPatch,
        removed: str,
    ) -> None:
        """``extra="ignore"`` would otherwise drop these without a word."""
        monkeypatch.setenv(removed, "user_metadata")
        with pytest.raises(ValueError, match="no longer supported"):
            get_http_client_settings()


class TestEgressRoutes:
    @pytest.mark.ai
    def test_no_proxy_host_yields_direct_egress(self) -> None:
        settings = HttpClientSettings()
        route = build_route(settings, resolve_identity(settings, _context()))

        assert isinstance(route, DirectRoute)

    @pytest.mark.ai
    def test_proxy_without_auth_mode_is_still_proxied(self) -> None:
        settings = HttpClientSettings(
            proxy_auth_mode="none",
            proxy_host="proxy.example.com",
            proxy_port=8080,
        )
        route = build_route(settings, resolve_identity(settings, _context()))

        assert isinstance(route, ProxiedRoute)
        assert route.proxy.auth is None

    @pytest.mark.ai
    def test_build_route_puts_credentials_on_the_proxy_object(self) -> None:
        settings = _proxy_settings(
            proxy_password=LogSecretStr(""),
            proxy_headers={"X-Custom": LogSecretStr("value")},
        )
        route = build_route(settings, resolve_identity(settings, _context()))

        assert isinstance(route, ProxiedRoute)
        assert route.proxy.headers["X-Custom"] == "value"
        assert str(route.proxy.url) == "http://proxy.example.com:8080"
        assert route.proxy.auth == ("technical", "")

    @pytest.mark.ai
    def test_build_route_keeps_special_characters_out_of_the_url(self) -> None:
        settings = _proxy_settings(proxy_username=LogSecretStr("ignored"))
        route = build_route(
            settings,
            ProxyIdentity(username="user:with@special/chars", password=""),
        )

        assert isinstance(route, ProxiedRoute)
        assert str(route.proxy.url) == "http://proxy.example.com:8080"
        assert route.proxy.auth == ("user:with@special/chars", "")

    @pytest.mark.ai
    def test_no_extra_headers_when_nothing_is_configured(self) -> None:
        settings = _proxy_settings()
        route = build_route(settings, resolve_identity(settings, _context()))

        assert isinstance(route, ProxiedRoute)
        assert _UID_HEADER not in route.proxy.headers


class TestProxyIdentityOnTheConnect:
    @pytest.mark.ai
    def test_service_credentials_and_uid_coexist(self) -> None:
        """Hop B carries authenticity and attribution at the same time."""
        settings = _proxy_settings(proxy_user_id_header=_UID_HEADER)
        route = build_route(
            settings,
            resolve_identity(settings, _context({"userName": "u12345"})),
        )

        assert isinstance(route, ProxiedRoute)
        assert route.proxy.auth == ("technical", "secret")
        assert route.proxy.headers[_UID_HEADER] == "u12345"

    @pytest.mark.ai
    def test_static_headers_and_uid_merge(self) -> None:
        settings = _proxy_settings(
            proxy_user_id_header=_UID_HEADER,
            proxy_headers={"X-Tenant": LogSecretStr("acme")},
        )
        route = build_route(
            settings,
            resolve_identity(settings, _context({"userName": "u12345"})),
        )

        assert isinstance(route, ProxiedRoute)
        assert route.proxy.headers["X-Tenant"] == "acme"
        assert route.proxy.headers[_UID_HEADER] == "u12345"

    @pytest.mark.ai
    def test_per_request_uid_wins_over_a_colliding_static_header(self) -> None:
        settings = _proxy_settings(
            proxy_user_id_header=_UID_HEADER,
            proxy_headers={_UID_HEADER: LogSecretStr("stale-from-settings")},
        )
        route = build_route(
            settings,
            resolve_identity(settings, _context({"userName": "u12345"})),
        )

        assert isinstance(route, ProxiedRoute)
        assert route.proxy.headers[_UID_HEADER] == "u12345"

    @pytest.mark.ai
    def test_nothing_proxy_bound_reaches_the_target_request(self) -> None:
        """The hop guard: proxy headers belong to the CONNECT, not the target.

        ``proxy_headers`` used to be attached to the client's default headers,
        so a documented ``{"Proxy-Authorization": "..."}`` would have been sent
        straight to the search engine.
        """
        settings = _proxy_settings(
            proxy_user_id_header=_UID_HEADER,
            proxy_headers={"Proxy-Authorization": LogSecretStr("Basic leaked")},
        )
        identity = resolve_identity(settings, _context({"userName": "u12345"}))
        client = build_async_client(settings, identity, timeout=1.0)

        assert "Proxy-Authorization" not in client.headers
        assert _UID_HEADER not in client.headers

    @pytest.mark.ai
    def test_uid_metadata_field_is_configurable(self) -> None:
        settings = _proxy_settings(
            proxy_user_id_header=_UID_HEADER,
            proxy_user_id_metadata_field="email",
        )
        identity = resolve_identity(
            settings,
            _context({"userName": "u12345", "email": "a@b.com"}),
        )
        assert identity.end_user_id == "a@b.com"

    @pytest.mark.ai
    def test_identity_is_anonymous_when_proxy_auth_is_off(self) -> None:
        settings = HttpClientSettings(proxy_auth_mode="none")
        assert resolve_identity(settings, _context()).is_anonymous

    @pytest.mark.ai
    def test_missing_uid_fails_closed(self) -> None:
        settings = _proxy_settings(proxy_user_id_header=_UID_HEADER)
        with pytest.raises(ValidationProxyError, match="userName"):
            resolve_identity(settings, _context({}))

    @pytest.mark.ai
    def test_blank_uid_fails_closed(self) -> None:
        settings = _proxy_settings(proxy_user_id_header=_UID_HEADER)
        with pytest.raises(ValidationProxyError, match="userName"):
            resolve_identity(settings, _context({"userName": "   "}))

    @pytest.mark.ai
    def test_uid_is_not_resolved_when_no_header_is_configured(self) -> None:
        settings = _proxy_settings()
        identity = resolve_identity(settings, _context({}))
        assert identity.end_user_id == ""


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
