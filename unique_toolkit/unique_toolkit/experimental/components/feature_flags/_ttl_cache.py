import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from cachetools import LRUCache, TTLCache


class AsyncTTLCache:
    """Per-key async TTL cache with stampede protection.

    Uses a per-key asyncio.Lock to ensure only one coroutine fetches a
    value on a cache miss; subsequent waiters reuse the fetched result.
    Both the value cache and the lock dict are bounded by ``maxsize``.
    """

    def __init__(self, *, maxsize: int = 1024, ttl: float = 30.0) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._locks: LRUCache[str, asyncio.Lock] = LRUCache(maxsize=maxsize)
        self._dict_lock = asyncio.Lock()

    async def _get_key_lock(self, key: str) -> asyncio.Lock:
        async with self._dict_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, bool]:
        """Return ``(value, from_cache)`` for *key*.

        If the value is present in the cache, returns it immediately with
        ``from_cache=True``. On a miss, acquires a per-key lock, rechecks,
        then calls ``await fetcher()`` and stores the result. If the fetcher
        raises, the exception propagates and nothing is cached.
        """
        cached = self._cache.get(key)
        if cached is not None:
            return cached, True

        key_lock = await self._get_key_lock(key)
        async with key_lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached, True

            value = await fetcher()
            self._cache[key] = value
            return value, False
