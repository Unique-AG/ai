"""Per-worker limit on crawl requests running at once."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from unique_search_proxy_core.errors import RateLimitedError

_RETRY_AFTER_SECONDS = 1


class CrawlLimiter:
    """Admits at most ``max_concurrent`` crawls and rejects the rest.

    Rejecting instead of queueing keeps a burst from piling bodies up in one
    worker; callers retry on the 429.
    """

    def __init__(self, max_concurrent: int) -> None:
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        """Hold one crawl slot for the duration of the block.

        Raises:
            RateLimitedError: Every slot is taken.
        """
        if self._semaphore.locked():
            raise RateLimitedError(
                f"Crawl capacity is in use ({self._max_concurrent} concurrent "
                "crawls per worker)",
                retry_after_seconds=_RETRY_AFTER_SECONDS,
            )
        async with self._semaphore:
            yield


def get_crawl_limiter(app: FastAPI) -> CrawlLimiter:
    """Return the application-owned crawl limiter."""
    limiter = getattr(app.state, "crawl_limiter", None)
    if limiter is None:
        raise RuntimeError("Crawl limiter is not initialized")
    return limiter


__all__ = ["CrawlLimiter", "get_crawl_limiter"]
