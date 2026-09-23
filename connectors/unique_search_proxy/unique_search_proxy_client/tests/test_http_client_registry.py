"""HttpClientRegistry: one client per proxy identity."""

from __future__ import annotations

import pytest
from unique_search_proxy_core.context import RequestContext

from unique_search_proxy_client.web.core.client.service import HttpClientRegistry
from unique_search_proxy_client.web.settings.client import HttpClientSettings
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr

_UID_HEADER = "X-Unique-End-User-Id"


def _settings(**overrides: object) -> HttpClientSettings:
    defaults: dict[str, object] = {
        "proxy_auth_mode": "username_password",
        "proxy_host": "proxy.example.com",
        "proxy_port": 8080,
        "proxy_username": LogSecretStr("technical"),
        "proxy_password": LogSecretStr(""),
        "proxy_user_id_header": _UID_HEADER,
        "http_client_cache_size": 128,
    }
    defaults.update(overrides)
    return HttpClientSettings(**defaults)  # type: ignore[arg-type]


def _context(
    username: str,
    *,
    company_id: str = "company-a",
) -> RequestContext:
    return RequestContext(
        company_id=company_id,
        user_id="user-1",
        chat_id="chat-1",
        user_metadata={"userName": username},
    )


def _registry(settings: HttpClientSettings) -> HttpClientRegistry:
    return HttpClientRegistry(settings=settings)


@pytest.mark.ai
class TestHttpClientRegistry:
    async def test_without_uid_header_one_client_serves_everyone(self) -> None:
        settings = _settings(proxy_user_id_header=None)
        registry = _registry(settings)
        try:
            first = await registry.client_for(_context("ignored"))
            again = await registry.client_for(_context("other"))
            assert first is again
            assert registry.size == 1
        finally:
            await registry.aclose()

    def test_constructs_without_opening_clients(self) -> None:
        registry = _registry(_settings())
        assert registry.size == 0

    async def test_uid_header_isolates_clients_per_user(self) -> None:
        """The regression guard for cross-user misattribution.

        Every user shares the same service credentials, so only the UID in the
        cache key keeps one user's CONNECT header off another user's tunnel.
        """
        registry = _registry(_settings())
        try:
            first = await registry.client_for(_context("u1"))
            again = await registry.client_for(_context("u1"))
            other = await registry.client_for(_context("u2"))

            assert first is again
            assert first is not other
            assert registry.size == 2
        finally:
            await registry.aclose()

    async def test_evicts_least_recently_used_client(self) -> None:
        registry = _registry(_settings(http_client_cache_size=2))
        try:
            await registry.client_for(_context("u1"))
            second = await registry.client_for(_context("u2"))
            await registry.client_for(_context("u1"))
            await registry.client_for(_context("u3"))

            assert registry.size == 2
            assert second.is_closed
        finally:
            await registry.aclose()

    async def test_evicted_client_is_closed(self) -> None:
        registry = _registry(_settings(http_client_cache_size=1))
        try:
            evicted = await registry.client_for(_context("u1"))
            fresh = await registry.client_for(_context("u2"))
            assert evicted.is_closed
            assert not fresh.is_closed
        finally:
            await registry.aclose()

    async def test_aclose_closes_every_client(self) -> None:
        registry = _registry(_settings())
        first = await registry.client_for(_context("u1"))
        second = await registry.client_for(_context("u2"))

        await registry.aclose()

        assert first.is_closed
        assert second.is_closed
        assert registry.size == 0
        assert registry.is_open is False
