"""Tests for unique_toolkit.experimental.resources.feature_flags._ttl_cache."""

from __future__ import annotations

import asyncio

import pytest

from unique_toolkit.experimental.resources.feature_flags._ttl_cache import (
    AsyncTTLCache,
)


@pytest.mark.ai
async def test_get_or_fetch__keeps_stale_value__by_default() -> None:
    """
    Purpose: Verify get_stale() finds a value after get_or_fetch(), with default settings.
    Why this matters: This is the existing behavior feature_flags.client relies on for
    its stale-on-fetch-failure fallback — must not regress.
    """
    cache = AsyncTTLCache(maxsize=8, ttl_ms=5_000)

    async def fetcher() -> str:
        return "v"

    await cache.get_or_fetch("k", fetcher)

    value, hit = cache.get_stale("k")
    assert (value, hit) == ("v", True)


@pytest.mark.ai
async def test_get_or_fetch__does_not_keep_stale_value__when_disabled() -> None:
    """
    Purpose: Verify get_stale() finds nothing after get_or_fetch() when keep_stale=False.
    Why this matters: A caller that never reads get_stale() (e.g. kb-mcp's content-tree
    tool) shouldn't pay to retain large values indefinitely in the LRU-only fallback —
    that fallback is bounded by key count, not time, so with low key turnover it can
    hold values far longer than ttl_ms suggests.
    """
    cache = AsyncTTLCache(maxsize=8, ttl_ms=5_000, keep_stale=False)

    async def fetcher() -> str:
        return "v"

    await cache.get_or_fetch("k", fetcher)

    value, hit = cache.get_stale("k")
    assert (value, hit) == (None, False)


@pytest.mark.ai
async def test_get_or_fetch__returns_cached_value__when_disabled() -> None:
    """
    Purpose: Verify keep_stale=False doesn't affect the normal TTL-cache hit/miss path,
    and that a cache hit (not just the initial fetch) doesn't write into the stale
    fallback either.
    Why this matters: keep_stale only controls the separate fallback cache; the primary
    cache behavior (and the fetcher's call count) must be unaffected. The hit path is a
    separate write site from the post-fetch write — after warm-up it's also the
    dominant path, so it needs its own coverage rather than relying on the post-fetch
    assertion alone.
    """
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
    """
    Purpose: Verify the locked re-check path — a second concurrent caller that finds
    the value already fetched while waiting on the per-key lock — doesn't write into
    the stale fallback when keep_stale=False.
    Why this matters: this is a third, distinct write site from the hot-path cache hit
    and the post-fetch write; exercising only those two would leave this one unguarded.
    """
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
