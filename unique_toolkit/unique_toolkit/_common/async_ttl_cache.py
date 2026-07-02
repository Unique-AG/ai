import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from cachetools import LRUCache, TTLCache

# Sentinel for distinguishing a stored False/None from a missing key.
# Never stored as a value; only used as the default in .get() calls.
_MISSING = object()


class AsyncTTLCache:
    """Per-key async TTL cache with stampede protection.

    Uses a per-key asyncio.Lock to ensure only one coroutine fetches a
    value on a cache miss; subsequent waiters reuse the fetched result.
    Both the value cache and the lock dict are bounded by ``maxsize``.

    Keys may be any hashable — strings, tuples, etc.
    """

    def __init__(self, *, maxsize: int = 1024, ttl_ms: float = 5_000) -> None:
        self._cache: TTLCache[Any, Any] = TTLCache(maxsize=maxsize, ttl=ttl_ms / 1000)
        self._stale: LRUCache[Any, Any] = LRUCache(maxsize=maxsize)
        self._locks: LRUCache[Any, asyncio.Lock] = LRUCache(maxsize=maxsize)
        self._dict_lock = asyncio.Lock()

    async def _get_key_lock(self, key: Any) -> asyncio.Lock:
        async with self._dict_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    async def get_or_fetch(
        self,
        key: Any,
        fetcher: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, bool]:
        """Return ``(value, from_cache)``, fetching on a miss with per-key stampede protection."""
        cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            self._stale[key] = cached  # keep stale warm while TTL cache is hot
            return cached, True

        # Acquire per-key lock; re-check inside in case another waiter already fetched.
        key_lock = await self._get_key_lock(key)
        async with key_lock:
            cached = self._cache.get(key, _MISSING)
            if cached is not _MISSING:
                self._stale[key] = cached  # keep stale warm while TTL cache is hot
                return cached, True

            value = await fetcher()
            self._cache[key] = value
            self._stale[key] = value
            return value, False

    def get_stale(self, key: Any) -> tuple[Any, bool]:
        """Return ``(value, True)`` if a prior successful fetch exists for *key*, else ``(None, False)``."""
        value = self._stale.get(key, _MISSING)
        if value is _MISSING:
            return None, False
        return value, True

    def clear(self) -> None:
        """Drop all cached values and per-key locks."""
        self._cache.clear()
        self._stale.clear()
        self._locks.clear()
