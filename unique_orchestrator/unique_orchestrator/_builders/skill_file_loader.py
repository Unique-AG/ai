"""Download ``SKILL.md`` files for the Skill tool, and cache the parsed result.

A space can list a hundred skills, and every turn needs the name and
description of each. Downloading all files at once on every turn overloads
the content API, so downloads share one process-wide limit and are retried,
and a skill the platform vouches for is parsed once and then served from
memory.

A cache hit skips the content API and its access check, so the cache is only
used for a skill the platform has just listed as readable for the acting
user. ``fetch_readable_skill_versions`` asks for that list once per turn, as
the user. The skill list in the message is never trusted for this: it comes
from the client. A skill that is not in the platform's list is downloaded as
the user and not cached.
"""

from __future__ import annotations

import asyncio
import random
import threading
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from logging import Logger
from typing import TYPE_CHECKING

from unique_skill_tool.loader import parse_skill_file
from unique_skill_tool.schemas import SkillDefinition
from unique_toolkit.app.schemas import SkillReference
from unique_toolkit.skills import get_readable_skill_versions_async

if TYPE_CHECKING:
    from unique_toolkit.content.service import ContentService

MAX_PARALLEL_SKILL_DOWNLOADS = 10
SKILL_DOWNLOAD_TIMEOUT_S = 20.0
SKILL_DOWNLOAD_ATTEMPTS = 2
SKILL_DOWNLOAD_BACKOFF_S = 0.25
MAX_SKILL_FILE_BYTES = 1_000_000
SKILL_CACHE_MAX_ENTRIES = 2048

# Company, content id and the file's last-modified time. An edited file gets
# a new last-modified time, so it never matches the entry of the old text.
SkillCacheKey = tuple[str, str, str]

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class _DownloadLimiter:
    """One limit on parallel skill downloads for every turn in this process."""

    def __init__(self, *, max_parallel: int) -> None:
        self._max_parallel = max_parallel
        self._semaphores: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}
        self._lock = threading.Lock()

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        async with self._semaphore():
            yield

    def _semaphore(self) -> asyncio.Semaphore:
        # A semaphore belongs to one event loop, so each loop gets its own.
        loop = asyncio.get_running_loop()
        with self._lock:
            for known in [known for known in self._semaphores if known.is_closed()]:
                del self._semaphores[known]
            semaphore = self._semaphores.get(loop)
            if semaphore is None:
                semaphore = asyncio.Semaphore(self._max_parallel)
                self._semaphores[loop] = semaphore
            return semaphore


class SkillCache:
    """Parsed skills by ``SkillCacheKey``, least recently used evicted first.

    ``None`` is a valid entry: the file was read and is not a usable skill.
    """

    def __init__(self, *, max_entries: int) -> None:
        self._max_entries = max_entries
        self._entries: OrderedDict[SkillCacheKey, SkillDefinition | None] = (
            OrderedDict()
        )
        self._loading: dict[
            tuple[asyncio.AbstractEventLoop, SkillCacheKey],
            asyncio.Task[SkillDefinition | None],
        ] = {}
        self._lock = threading.Lock()

    async def get_or_load(
        self,
        *,
        key: SkillCacheKey,
        load: Callable[[], Awaitable[SkillDefinition | None]],
    ) -> tuple[SkillDefinition | None, bool]:
        """Return the skill and whether it came from the cache.

        Turns that need the same uncached skill at the same time share one
        ``load`` call. A failed ``load`` raises for each of them and stores
        nothing.
        """
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key], True
            loading_key = (asyncio.get_running_loop(), key)
            task = self._loading.get(loading_key)
            if task is None:
                task = asyncio.ensure_future(self._load_and_store(key=key, load=load))
                self._loading[loading_key] = task
                task.add_done_callback(
                    lambda done: self._finish_loading(
                        loading_key=loading_key, task=done
                    )
                )
        # Shielded so a cancelled turn does not cancel the download for the
        # other turns that wait on it.
        return await asyncio.shield(task), False

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    async def _load_and_store(
        self,
        *,
        key: SkillCacheKey,
        load: Callable[[], Awaitable[SkillDefinition | None]],
    ) -> SkillDefinition | None:
        skill = await load()
        with self._lock:
            self._entries[key] = skill
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
        return skill

    def _finish_loading(
        self,
        *,
        loading_key: tuple[asyncio.AbstractEventLoop, SkillCacheKey],
        task: asyncio.Task[SkillDefinition | None],
    ) -> None:
        with self._lock:
            self._loading.pop(loading_key, None)
        if not task.cancelled():
            # Read so a failure nobody awaited any more is not reported as
            # "Task exception was never retrieved".
            task.exception()


_download_limiter = _DownloadLimiter(max_parallel=MAX_PARALLEL_SKILL_DOWNLOADS)
_skill_cache = SkillCache(max_entries=SKILL_CACHE_MAX_ENTRIES)


def clear_skill_cache() -> None:
    """Empty the process-wide skill cache."""
    _skill_cache.clear()


async def fetch_readable_skill_versions(
    *,
    user_id: str,
    company_id: str,
    space_id: str,
    logger: Logger,
) -> dict[str, str]:
    """Return content id to last-modified time for the skills the user can read.

    Empty when the platform cannot answer, for example an older platform
    without this endpoint. Every skill is then downloaded as the user.
    """
    try:
        return await get_readable_skill_versions_async(
            user_id=user_id, company_id=company_id, space_id=space_id
        )
    except Exception:
        logger.warning(
            "Could not list the readable skills of space '%s' — "
            "loading every skill without the cache.",
            space_id,
            exc_info=True,
        )
        return {}


async def load_skill(
    *,
    content_service: ContentService,
    reference: SkillReference,
    company_id: str,
    readable_version: str | None,
    logger: Logger,
) -> tuple[SkillDefinition | None, bool]:
    """Return the parsed skill and whether it came from the cache.

    ``readable_version`` is the skill file's last-modified time from the
    platform's list of skills the acting user can read, or ``None`` when the
    skill is not in that list. Only a listed skill uses the cache.

    ``None`` as the skill means the file is not a usable skill. A failed
    download raises.
    """

    async def fetch() -> SkillDefinition | None:
        return await _download_and_parse(
            content_service=content_service, reference=reference, logger=logger
        )

    if not readable_version or not company_id:
        return await fetch(), False

    skill, from_cache = await _skill_cache.get_or_load(
        key=(company_id, reference.content_id, readable_version), load=fetch
    )
    # Callers get their own copy, so no turn can change the cached skill.
    return (skill.model_copy() if skill is not None else None), from_cache


async def _download_and_parse(
    *,
    content_service: ContentService,
    reference: SkillReference,
    logger: Logger,
) -> SkillDefinition | None:
    label = reference.name or reference.content_id
    payload = await _download(
        content_service=content_service, content_id=reference.content_id
    )
    if len(payload) > MAX_SKILL_FILE_BYTES:
        logger.warning(
            "Skipping skill '%s' (%s): file is %d bytes, the limit is %d.",
            label,
            reference.content_id,
            len(payload),
            MAX_SKILL_FILE_BYTES,
        )
        return None
    try:
        file_text = payload.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning(
            "Skipping skill '%s' (%s): file is not valid UTF-8.",
            label,
            reference.content_id,
        )
        return None
    return parse_skill_file(
        file_text=file_text,
        content_id=reference.content_id,
        source_label=label,
        logger=logger,
    )


async def _download(*, content_service: ContentService, content_id: str) -> bytes:
    for attempt in range(1, SKILL_DOWNLOAD_ATTEMPTS + 1):
        try:
            async with _download_limiter.slot():
                return await content_service.download_content_to_bytes_async(
                    content_id=content_id, timeout=SKILL_DOWNLOAD_TIMEOUT_S
                )
        except Exception as error:
            if attempt == SKILL_DOWNLOAD_ATTEMPTS or not _is_retryable(error):
                raise
        # Outside the slot, so a waiting retry does not hold up other downloads.
        await asyncio.sleep(SKILL_DOWNLOAD_BACKOFF_S * attempt * (1 + random.random()))
    raise AssertionError("unreachable: the last attempt returns or raises")


def _is_retryable(error: Exception) -> bool:
    """A download is safe to repeat, so only a definite client error is final."""
    status_code = getattr(getattr(error, "response", None), "status_code", None)
    return not isinstance(status_code, int) or status_code in _RETRYABLE_STATUS_CODES
