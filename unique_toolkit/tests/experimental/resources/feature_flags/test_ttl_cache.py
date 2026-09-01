"""Tests for unique_toolkit.experimental.resources.feature_flags._ttl_cache."""

from __future__ import annotations

import asyncio

import pytest

from unique_toolkit.experimental.resources.feature_flags._ttl_cache import (
    AsyncTTLCache,
)


@pytest.mark.ai
async def test_get_or_fetch__keeps_stale_value__by_default() -> None:
    cache = AsyncTTLCache(maxsize=8, ttl_ms=5_000)

    async def fetcher() -> str:
        return "v"

    await cache.get_or_fetch("k", fetcher)

    value, hit = cache.get_stale("k")
    assert (value, hit) == ("v", True)


@pytest.mark.ai
async def test_get_or_fetch__does_not_keep_stale_value__when_disabled() -> None:
    cache = AsyncTTLCache(maxsize=8, ttl_ms=5_000, keep_stale=False)

    async def fetcher() -> str:
        return "v"

    await cache.get_or_fetch("k", fetcher)

    value, hit = cache.get_stale("k")
    assert (value, hit) == (None, False)


@pytest.mark.ai
async def test_get_or_fetch__returns_cached_value__when_disabled() -> None:
    cache = AsyncTTLCache(maxsize=8, ttl_ms=5_000, keep_stale=False)
    calls = 0

    async def fetcher() -> str:
        nonlocal calls
        calls += 1
        return "v"

    first, first_hit = await cache.get_or_fetch("k", fetcher)
    second, second_hit = await cache.get_or_fetch("k", fetcher)

    assert (first, first_hit) == ("v", False)
    assert (second, second_hit) == ("v", True)
    assert calls == 1
    assert cache.get_stale("k") == (None, False)


@pytest.mark.ai
async def test_get_or_fetch__stale_guarded__on_locked_recheck__when_disabled() -> None:
    cache = AsyncTTLCache(maxsize=8, ttl_ms=5_000, keep_stale=False)

    async def fetcher() -> str:
        await asyncio.sleep(0.01)
        return "v"

    async def unexpected_fetcher() -> str:
        raise AssertionError("second caller should reuse the first fetch, not refetch")

    first = asyncio.create_task(cache.get_or_fetch("k", fetcher))
    await asyncio.sleep(0)  # let `first` acquire the key lock and start fetching
    second = asyncio.create_task(cache.get_or_fetch("k", unexpected_fetcher))

    results = await asyncio.gather(first, second)

    assert results == [("v", False), ("v", True)]
    assert cache.get_stale("k") == (None, False)
