from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.errors import (
    BadRequestProxyError,
    ValidationProxyError,
)

from unique_search_proxy_client.web.api.v1.crawl import _http_client_for_crawl
from unique_search_proxy_client.web.context import (
    bind_request_context,
    reset_request_context,
)
from unique_search_proxy_client.web.core.client.per_user import (
    PerUserProxyClientCache,
)
from unique_search_proxy_client.web.core.client.service import HttpClientPool
from unique_search_proxy_client.web.settings.client import HttpClientSettings
from unique_search_proxy_client.web.settings.secret_str import LogSecretStr


def _settings(*, cache_size: int = 2) -> HttpClientSettings:
    return HttpClientSettings(
        proxy_host="proxy.example.com",
        proxy_port=8080,
        per_user_proxy_company_ids=["company-1"],
        per_user_proxy_password=LogSecretStr("placeholder"),
        per_user_proxy_client_cache_size=cache_size,
    )


def _context(external_user_id: str | None = "client-user") -> RequestContext:
    return RequestContext(
        company_id="company-1",
        user_id="internal-user",
        chat_id="chat-1",
        external_user_id=external_user_id,
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_cache_reuses_client_for_same_company_and_external_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock(spec=httpx.AsyncClient)
    build_client = MagicMock(return_value=client)
    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.client.per_user.build_per_user_async_client",
        build_client,
    )
    settings = _settings()
    cache = PerUserProxyClientCache(settings)

    first = await cache.get_client(_context())
    second = await cache.get_client(_context())

    assert first is client
    assert second is client
    build_client.assert_called_once_with("client-user", settings=settings)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_cache_evicts_and_closes_least_recently_used_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = MagicMock(spec=httpx.AsyncClient)
    second = MagicMock(spec=httpx.AsyncClient)
    build_client = MagicMock(side_effect=[first, second])
    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.client.per_user.build_per_user_async_client",
        build_client,
    )
    cache = PerUserProxyClientCache(_settings(cache_size=1))

    await cache.get_client(_context("first-user"))
    await cache.get_client(_context("second-user"))

    assert cache.size == 1
    first.aclose.assert_awaited_once()
    second.aclose.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_cache_fails_closed_when_external_user_id_is_missing() -> None:
    cache = PerUserProxyClientCache(_settings())

    with pytest.raises(ValidationProxyError, match="External user ID"):
        await cache.get_client(_context(None))


@pytest.mark.ai
def test_cache_rejects_missing_placeholder_password() -> None:
    settings = _settings().model_copy(update={"per_user_proxy_password": None})

    with pytest.raises(ValueError, match="password must be configured"):
        PerUserProxyClientCache(settings)


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_selects_per_user_client_for_gated_basic_crawler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shared_client = MagicMock(spec=httpx.AsyncClient)
    per_user_client = MagicMock(spec=httpx.AsyncClient)
    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.client.per_user.build_per_user_async_client",
        MagicMock(return_value=per_user_client),
    )
    cache = PerUserProxyClientCache(_settings())
    app = SimpleNamespace(
        state=SimpleNamespace(
            http_client_pool=HttpClientPool(client=shared_client),
            per_user_proxy_client_cache=cache,
        )
    )
    request = SimpleNamespace(app=app)
    token = bind_request_context(_context())
    try:
        selected = await _http_client_for_crawl(request, CrawlerType.BASIC.value)  # type: ignore[arg-type]
    finally:
        reset_request_context(token)

    assert selected is per_user_client


@pytest.mark.ai
@pytest.mark.asyncio
async def test_crawl_rejects_other_crawlers_for_gated_company() -> None:
    cache = PerUserProxyClientCache(_settings())
    app = SimpleNamespace(
        state=SimpleNamespace(
            http_client_pool=HttpClientPool(client=MagicMock(spec=httpx.AsyncClient)),
            per_user_proxy_client_cache=cache,
        )
    )
    request = SimpleNamespace(app=app)
    token = bind_request_context(_context())
    try:
        with pytest.raises(BadRequestProxyError, match="only supported"):
            await _http_client_for_crawl(request, "Firecrawl")  # type: ignore[arg-type]
    finally:
        reset_request_context(token)
