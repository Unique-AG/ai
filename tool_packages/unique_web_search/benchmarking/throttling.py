"""Per-engine rate-limit handling for the fetch stage.

A rate limit is a property of the *engine*, not of the request that happened to
trip it: when Google CSE returns 429, every other in-flight Google query is
about to get one too. Retrying per request therefore makes things worse — the
arm keeps hammering a closed door. So the backoff here is **shared per engine**:
one 429 parks the whole arm for a cooldown while the other engines keep running
at full speed.

Three levels, matching the three ways a fetch stage actually fails:

- a transient blip (proxy restart, reset connection) → retried, invisible;
- a per-minute/burst throttle → the arm pauses, then resumes and finishes;
- a daily quota that is simply gone → the arm *trips* after a few fruitless
  cooldowns and the remaining items fail fast without sending a request, so the
  other engines aren't held up. Those items are recorded as errors, which is
  exactly what the resume logic retries on the next run (see `completed_ids`).

The one failure that is *not* engine-scoped is a timeout waiting for an answer:
that is the question being slow, not the engine being closed, so it never parks
the arm (see `ITEM_SCOPED_ERRORS`).
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from unique_search_proxy_core.errors import ProxyError, UpstreamTimeoutError

T = TypeVar("T")

# Transport failures worth the same treatment as a 429: the item is fine, the
# moment isn't. (A proxy that is down for good still ends in a tripped arm.)
TRANSIENT_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.PoolTimeout,
)

# The exception to the per-engine rule: a timeout waiting for the *answer* is a
# property of the question, not of the engine. Agent engines think for minutes on
# a hard question, and `UpstreamTimeoutError` is `retryable=True` for a caller who
# may want the item again — but parking the whole arm and re-sending a call that
# already burned its full server-side budget stalls every other in-flight item to
# buy nothing. So these are recorded as errors and left to the resume logic, the
# same treatment tripped items get.
ITEM_SCOPED_ERRORS = (UpstreamTimeoutError, httpx.ReadTimeout)


class EngineHalted(Exception):
    """The arm tripped its breaker — raised without sending a request."""


def is_retryable(exc: BaseException) -> bool:
    """Whether this failure is worth an *arm-wide* cooldown and another attempt.

    Proxy errors carry their own verdict (``EmptySearchResultsError`` and bad
    requests are `retryable=False`; 429s and upstream 5xx are True), except for
    the item-scoped ones — see :data:`ITEM_SCOPED_ERRORS`.
    """
    if isinstance(exc, ITEM_SCOPED_ERRORS):
        return False
    if isinstance(exc, ProxyError):
        return exc.retryable
    return isinstance(exc, TRANSIENT_ERRORS)


class EngineThrottle:
    """Concurrency limit + shared cooldown gate + circuit breaker for one arm.

    Args:
        engine: Arm name, used in log lines.
        concurrency: Max in-flight requests for this engine.
        max_attempts: Attempts per item before its error is recorded.
        base_delay: First cooldown, in seconds; doubles each episode.
        max_delay: Cooldown ceiling, in seconds.
        max_episodes: Consecutive cooldowns with no success in between before
            the arm trips. Reset by any successful fetch.
    """

    def __init__(
        self,
        engine: str,
        *,
        concurrency: int = 8,
        max_attempts: int = 5,
        base_delay: float = 2.0,
        max_delay: float = 300.0,
        max_episodes: int = 6,
    ) -> None:
        self.engine = engine
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_episodes = max_episodes
        self._semaphore = asyncio.Semaphore(concurrency)
        self._lock = asyncio.Lock()
        self.reset()

    def reset(self) -> None:
        """Clear the breaker and counters. Called at the start of every fetch
        run: in the interactive window the throttles are built once in their own
        cell, so without this a re-run of the Run cell would start out halted."""
        self._resume_at = 0.0  # time.monotonic() the arm may fire again
        self._episodes = 0  # consecutive cooldowns without a success
        self.halted = False
        # counters for the throttling-summary cell
        self.retries = 0
        self.cooldowns = 0

    async def run(self, operation: Callable[[], Awaitable[T]]) -> tuple[T, float]:
        """Run ``operation``, retrying retryable failures behind the arm's gate.

        Returns the result and the latency of the *successful* attempt — waiting
        out a cooldown must not be charged to the engine's measured search time.
        """
        for attempt in range(1, self.max_attempts + 1):
            # Cheap pre-check so a halted arm drains without queueing.
            self._raise_if_halted()
            async with self._semaphore:
                # The gate MUST be inside the semaphore. Checking it before
                # acquiring means every task that queued for a slot while the
                # arm was healthy sails past the cooldown and fires the moment a
                # slot frees — thousands of doomed requests at full tilt, which
                # is the exact spam this class exists to prevent. Inside, only
                # `concurrency` tasks are ever in the cooldown; the rest are
                # still blocked on the semaphore and send nothing.
                await self._await_gate()
                self._raise_if_halted()  # may have tripped while we waited
                started = time.perf_counter()
                try:
                    result = await operation()
                except Exception as exc:
                    if not is_retryable(exc) or attempt == self.max_attempts:
                        raise
                    self.retries += 1
                    # Arm the cooldown before releasing the slot, so the next
                    # task in line sees it rather than racing past.
                    # `retry_after_seconds` exists only on RateLimitedError, and
                    # only when the proxy populates it; None means "use our own".
                    await self._open_cooldown(getattr(exc, "retry_after_seconds", None))
                else:
                    await self._note_success()
                    return result, time.perf_counter() - started
        raise AssertionError("unreachable: the last attempt re-raises")

    def _raise_if_halted(self) -> None:
        if self.halted:
            raise EngineHalted(
                f"{self.engine} arm halted after {self.max_episodes} consecutive "
                "rate-limit cooldowns; re-run the fetch cell to retry"
            )

    async def _await_gate(self) -> None:
        """Sleep until the arm's cooldown expires (jittered, so the waiters
        don't all fire in the same instant and re-trip the limit)."""
        while not self.halted:
            remaining = self._resume_at - time.monotonic()
            if remaining <= 0:
                return
            await asyncio.sleep(remaining + random.uniform(0, 0.5 * self.base_delay))

    async def _note_success(self) -> None:
        async with self._lock:
            self._episodes = 0

    async def _open_cooldown(self, retry_after: float | None) -> None:
        """Park the whole arm. Concurrent failures during one episode collapse
        into it rather than each doubling the delay — otherwise `concurrency`
        simultaneous 429s would jump straight to the ceiling."""
        async with self._lock:
            now = time.monotonic()
            if self.halted or now < self._resume_at:
                # Already parked by a sibling (ride out the same window), or the
                # arm is done for this run — either way, don't re-arm or re-log.
                return
            self._episodes += 1
            self.cooldowns += 1
            delay = min(self.base_delay * 2 ** (self._episodes - 1), self.max_delay)
            if retry_after is not None:
                delay = max(delay, retry_after)
            self._resume_at = now + delay
            if self._episodes >= self.max_episodes:
                self.halted = True
                self._resume_at = 0.0  # let parked tasks wake and fail fast
                print(
                    f"  [{self.engine}] halted after {self._episodes} cooldowns "
                    "with no success — remaining items recorded as errors, "
                    "re-run the fetch cell later to retry them"
                )
            else:
                print(
                    f"  [{self.engine}] retryable failure — arm paused {delay:.1f}s "
                    f"(episode {self._episodes}/{self.max_episodes}; "
                    "a success resets this)"
                )
