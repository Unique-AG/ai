"""Per-user proxy authentication: identity mapping, client build, and caching."""

from __future__ import annotations

import pytest
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError

from unique_search_proxy_client.web.core.client.per_user import (
    PerUserProxyClientCache,
    resolve_proxy_username,
)
from unique_search_proxy_client.web.core.client.service import (
    build_per_user_async_client,
    build_per_user_proxy,
)
from unique_search_proxy_client.web.settings.client import HttpClientSettings
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_GATED_COMPANY = "company-a"


def _settings(**overrides: object) -> HttpClientSettings:
    defaults: dict[str, object] = {
        "proxy_protocol": "http",
        "proxy_host": "proxy.example.com",
        "proxy_port": 8080,
        "per_user_proxy_company_ids": [_GATED_COMPANY],
        "per_user_proxy_password": LogSecretStr(""),
    }
    defaults.update(overrides)
    return HttpClientSettings(**defaults)  # type: ignore[arg-type]


def _context(
    user_metadata: dict[str, object] | None,
    *,
    company_id: str = _GATED_COMPANY,
) -> RequestContext:
    return RequestContext(
        company_id=company_id,
        user_id="user-1",
        chat_id="chat-1",
        user_metadata=user_metadata,
    )


@pytest.mark.ai
class TestResolveProxyUsername:
    def test_reads_the_configured_metadata_field(self) -> None:
        username = resolve_proxy_username(
            _context({"userName": "u12345", "email": "a@b.com"}),
            settings=_settings(),
        )
        assert username == "u12345"

    def test_field_is_configurable_rather_than_hardcoded(self) -> None:
        """Which metadata field identifies the user is a deployment decision."""
        username = resolve_proxy_username(
            _context({"userName": "u12345", "email": "a@b.com"}),
            settings=_settings(per_user_proxy_username_field="email"),
        )
        assert username == "a@b.com"

    def test_strips_surrounding_whitespace(self) -> None:
        username = resolve_proxy_username(
            _context({"userName": "  u12345  "}),
            settings=_settings(),
        )
        assert username == "u12345"

    @pytest.mark.parametrize(
        "user_metadata",
        [
            None,
            {},
            {"otherField": "u12345"},
            {"userName": ""},
            {"userName": "   "},
            {"userName": None},
            {"userName": 12345},
            {"userName": {"nested": "value"}},
        ],
    )
    def test_fails_closed_without_a_usable_identity(
        self,
        user_metadata: dict[str, object] | None,
    ) -> None:
        """Never fall back to the shared technical account: refuse the fetch."""
        with pytest.raises(ValidationProxyError):
            resolve_proxy_username(_context(user_metadata), settings=_settings())

    def test_error_names_the_configured_field(self) -> None:
        with pytest.raises(ValidationProxyError, match="email"):
            resolve_proxy_username(
                _context({"userName": "u12345"}),
                settings=_settings(per_user_proxy_username_field="email"),
            )


@pytest.mark.ai
class TestBuildPerUserProxy:
    def test_authenticates_as_the_user_with_the_placeholder_password(self) -> None:
        """BNPP's proxy expects Basic auth of ``<uid>:`` and applies that user's rights."""
        proxy = build_per_user_proxy("u12345", settings=_settings())

        assert proxy.auth == ("u12345", "")

    def test_uses_the_configured_placeholder_password(self) -> None:
        proxy = build_per_user_proxy(
            "u12345",
            settings=_settings(per_user_proxy_password=LogSecretStr("placeholder")),
        )

        assert proxy.auth == ("u12345", "placeholder")

    def test_credentials_stay_out_of_the_proxy_url(self) -> None:
        """Credentials on ``httpx.Proxy`` avoid percent-encoding pitfalls."""
        proxy = build_per_user_proxy("user:with@special/chars", settings=_settings())

        assert str(proxy.url) == "http://proxy.example.com:8080"
        assert proxy.auth == ("user:with@special/chars", "")

    def test_shared_technical_credentials_are_not_reused(self) -> None:
        """The point of the feature: egress must not present the shared account."""
        proxy = build_per_user_proxy(
            "u12345",
            settings=_settings(
                proxy_auth_mode="username_password",
                proxy_username=LogSecretStr("technical-account"),
                proxy_password=LogSecretStr("technical-secret"),
            ),
        )

        assert proxy.auth == ("u12345", "")
        assert "technical-account" not in str(proxy.url)

    def test_client_is_built_on_that_proxy(self) -> None:
        client = build_per_user_async_client("u12345", settings=_settings())

        assert client._mounts, "expected the client to route through a proxy"


@pytest.mark.ai
class TestPerUserProxyClientCache:
    async def test_only_gated_companies_are_enabled(self) -> None:
        cache = PerUserProxyClientCache(_settings())

        assert cache.enabled_for(_GATED_COMPANY) is True
        assert cache.enabled_for("company-z") is False

    async def test_reuses_one_client_per_user(self) -> None:
        cache = PerUserProxyClientCache(_settings())
        try:
            first = await cache.get_client(_context({"userName": "u1"}))
            again = await cache.get_client(_context({"userName": "u1"}))
            other = await cache.get_client(_context({"userName": "u2"}))

            assert first is again
            assert first is not other
            assert cache.size == 2
        finally:
            await cache.aclose()

    async def test_never_shares_a_client_between_users(self) -> None:
        """Sharing would send one user's request under another user's identity."""
        cache = PerUserProxyClientCache(_settings())
        try:
            first = await cache.get_client(_context({"userName": "u1"}))
            second = await cache.get_client(_context({"userName": "u2"}))

            assert first is not second
        finally:
            await cache.aclose()

    async def test_evicts_least_recently_used_client_when_full(self) -> None:
        cache = PerUserProxyClientCache(
            _settings(per_user_proxy_client_cache_size=2),
        )
        try:
            first = await cache.get_client(_context({"userName": "u1"}))
            await cache.get_client(_context({"userName": "u2"}))
            await cache.get_client(_context({"userName": "u1"}))
            await cache.get_client(_context({"userName": "u3"}))

            assert cache.size == 2
            assert await cache.get_client(_context({"userName": "u1"})) is first
        finally:
            await cache.aclose()

    async def test_evicted_client_is_closed(self) -> None:
        cache = PerUserProxyClientCache(
            _settings(per_user_proxy_client_cache_size=1),
        )
        try:
            evicted = await cache.get_client(_context({"userName": "u1"}))
            await cache.get_client(_context({"userName": "u2"}))

            assert evicted.is_closed
        finally:
            await cache.aclose()

    async def test_aclose_closes_every_client(self) -> None:
        cache = PerUserProxyClientCache(_settings())
        first = await cache.get_client(_context({"userName": "u1"}))
        second = await cache.get_client(_context({"userName": "u2"}))

        await cache.aclose()

        assert first.is_closed
        assert second.is_closed
        assert cache.size == 0

    async def test_rejects_requests_for_ungated_companies(self) -> None:
        cache = PerUserProxyClientCache(_settings())
        try:
            with pytest.raises(RuntimeError):
                await cache.get_client(
                    _context({"userName": "u1"}, company_id="company-z"),
                )
        finally:
            await cache.aclose()

    async def test_fails_closed_when_identity_is_missing(self) -> None:
        cache = PerUserProxyClientCache(_settings())
        try:
            with pytest.raises(ValidationProxyError):
                await cache.get_client(_context(None))
        finally:
            await cache.aclose()

    def test_rejects_incomplete_configuration_at_startup(self) -> None:
        """Fail at boot, not on the first gated request."""
        with pytest.raises(ValueError, match="Proxy host and port"):
            PerUserProxyClientCache(_settings(proxy_host=None, proxy_port=None))

        with pytest.raises(ValueError, match="password"):
            PerUserProxyClientCache(_settings(per_user_proxy_password=None))

    def test_accepts_incomplete_configuration_when_no_company_is_gated(self) -> None:
        cache = PerUserProxyClientCache(
            HttpClientSettings(per_user_proxy_company_ids=[]),
        )
        assert cache.size == 0
