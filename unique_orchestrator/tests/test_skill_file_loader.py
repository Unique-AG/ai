"""Tests for the skill file download limit, retry and cache."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from logging import Logger
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_skill_tool.schemas import SkillDefinition
from unique_toolkit.app.schemas import SkillReference

from unique_orchestrator._builders import skill_file_loader
from unique_orchestrator._builders.skill_file_loader import (
    MAX_PARALLEL_SKILL_DOWNLOADS,
    MAX_SKILL_FILE_BYTES,
    SKILL_DOWNLOAD_ATTEMPTS,
    SKILL_DOWNLOAD_TIMEOUT_S,
    SkillCache,
    clear_skill_cache,
    load_skill,
)
from unique_orchestrator._builders.skill_setup import load_selectable_skills

UPDATED_AT = "2026-11-20T10:00:00.000Z"


def _skill_file(name: str, description: str = "Does a thing.") -> bytes:
    return (
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\nbody\n"
    ).encode()


def _content_service(
    download: AsyncMock, *, company_id: str | None = "company-1"
) -> MagicMock:
    content_service = MagicMock()
    content_service.company_id = company_id
    content_service.download_content_to_bytes_async = download
    return content_service


def _reference(
    content_id: str = "cont-1",
    *,
    updated_at: str | None = UPDATED_AT,
    name: str = "pdf",
) -> SkillReference:
    return SkillReference(
        name=name, scope_id="scope-1", content_id=content_id, updated_at=updated_at
    )


class _HttpStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.response = MagicMock(status_code=status_code)


@pytest.fixture
def logger() -> Logger:
    return MagicMock(spec=Logger)


@pytest.fixture(autouse=True)
def _fresh_cache_and_no_backoff() -> Iterator[None]:
    clear_skill_cache()
    with patch.object(skill_file_loader, "SKILL_DOWNLOAD_BACKOFF_S", 0):
        yield
    clear_skill_cache()


class TestLoadSkillCache:
    async def test_stamped_skill_is_downloaded_once_and_then_served_from_cache(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(return_value=_skill_file("pdf"))
        content_service = _content_service(download)

        first, first_from_cache = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )
        second, second_from_cache = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )

        assert first is not None and first.name == "pdf"
        assert second == first
        assert (first_from_cache, second_from_cache) == (False, True)
        download.assert_awaited_once_with(
            content_id="cont-1", timeout=SKILL_DOWNLOAD_TIMEOUT_S
        )

    async def test_changed_updated_at_downloads_the_file_again(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(
            side_effect=[_skill_file("pdf", "Old."), _skill_file("pdf", "New.")]
        )
        content_service = _content_service(download)

        old, _ = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )
        new, from_cache = await load_skill(
            content_service=content_service,
            reference=_reference(updated_at="2026-11-21T08:00:00.000Z"),
            logger=logger,
        )

        assert old is not None and old.description == "Old."
        assert new is not None and new.description == "New."
        assert from_cache is False
        assert download.await_count == 2

    async def test_skill_without_updated_at_is_never_cached(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(return_value=_skill_file("pdf"))
        content_service = _content_service(download)
        reference = _reference(updated_at=None)

        _, first_from_cache = await load_skill(
            content_service=content_service, reference=reference, logger=logger
        )
        _, second_from_cache = await load_skill(
            content_service=content_service, reference=reference, logger=logger
        )

        assert (first_from_cache, second_from_cache) == (False, False)
        assert download.await_count == 2

    async def test_unstamped_request_does_not_read_a_stamped_cache_entry(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(return_value=_skill_file("pdf"))
        content_service = _content_service(download)
        await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )

        _, from_cache = await load_skill(
            content_service=content_service,
            reference=_reference(updated_at=None),
            logger=logger,
        )

        assert from_cache is False
        assert download.await_count == 2

    async def test_cache_is_not_shared_between_companies(self, logger: Logger) -> None:
        download = AsyncMock(return_value=_skill_file("pdf"))
        await load_skill(
            content_service=_content_service(download, company_id="company-1"),
            reference=_reference(),
            logger=logger,
        )

        _, from_cache = await load_skill(
            content_service=_content_service(download, company_id="company-2"),
            reference=_reference(),
            logger=logger,
        )

        assert from_cache is False
        assert download.await_count == 2

    async def test_skill_is_not_cached_without_a_company_id(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(return_value=_skill_file("pdf"))
        content_service = _content_service(download, company_id=None)

        await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )
        _, from_cache = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )

        assert from_cache is False
        assert download.await_count == 2

    async def test_changing_a_returned_skill_does_not_change_the_cached_one(
        self, logger: Logger
    ) -> None:
        content_service = _content_service(AsyncMock(return_value=_skill_file("pdf")))
        first, _ = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )
        assert first is not None
        first.description = "changed by a turn"

        second, _ = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )

        assert second is not None and second.description == "Does a thing."

    async def test_invalid_skill_file_is_cached_as_unusable(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(return_value=b"no frontmatter here")
        content_service = _content_service(download)

        first, _ = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )
        second, from_cache = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )

        assert first is None and second is None
        assert from_cache is True
        download.assert_awaited_once()

    async def test_failed_download_is_not_cached(self, logger: Logger) -> None:
        download = AsyncMock(
            side_effect=[_HttpStatusError(404), _skill_file("pdf")],
        )
        content_service = _content_service(download)

        with pytest.raises(_HttpStatusError):
            await load_skill(
                content_service=content_service, reference=_reference(), logger=logger
            )
        skill, from_cache = await load_skill(
            content_service=content_service, reference=_reference(), logger=logger
        )

        assert skill is not None and skill.name == "pdf"
        assert from_cache is False

    async def test_two_turns_loading_the_same_skill_share_one_download(
        self, logger: Logger
    ) -> None:
        release = asyncio.Event()

        async def slow_download(**_: object) -> bytes:
            await release.wait()
            return _skill_file("pdf")

        download = AsyncMock(side_effect=slow_download)
        content_service = _content_service(download)

        first_turn = asyncio.create_task(
            load_skill(
                content_service=content_service, reference=_reference(), logger=logger
            )
        )
        second_turn = asyncio.create_task(
            load_skill(
                content_service=content_service, reference=_reference(), logger=logger
            )
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        release.set()
        (first, _), (second, _) = await asyncio.gather(first_turn, second_turn)

        assert first is not None and second is not None
        assert first.name == second.name == "pdf"
        download.assert_awaited_once()

    async def test_cancelled_turn_does_not_cancel_the_shared_download(
        self, logger: Logger
    ) -> None:
        release = asyncio.Event()

        async def slow_download(**_: object) -> bytes:
            await release.wait()
            return _skill_file("pdf")

        download = AsyncMock(side_effect=slow_download)
        content_service = _content_service(download)

        cancelled_turn = asyncio.create_task(
            load_skill(
                content_service=content_service, reference=_reference(), logger=logger
            )
        )
        waiting_turn = asyncio.create_task(
            load_skill(
                content_service=content_service, reference=_reference(), logger=logger
            )
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        cancelled_turn.cancel()
        release.set()
        skill, _ = await waiting_turn

        assert skill is not None and skill.name == "pdf"
        download.assert_awaited_once()


class TestSkillCacheEviction:
    async def test_least_recently_used_entry_is_evicted_first(self) -> None:
        cache = SkillCache(max_entries=2)
        loads: list[str] = []

        def loader(content_id: str):
            async def load() -> SkillDefinition | None:
                loads.append(content_id)
                return None

            return load

        for content_id in ("a", "b"):
            await cache.get_or_load(key=("c", content_id, "t"), load=loader(content_id))
        await cache.get_or_load(key=("c", "a", "t"), load=loader("a"))
        await cache.get_or_load(key=("c", "c", "t"), load=loader("c"))

        _, a_from_cache = await cache.get_or_load(key=("c", "a", "t"), load=loader("a"))
        _, b_from_cache = await cache.get_or_load(key=("c", "b", "t"), load=loader("b"))

        assert a_from_cache is True
        assert b_from_cache is False
        assert loads == ["a", "b", "c", "b"]


class TestDownloadRetryAndLimit:
    @pytest.mark.parametrize(
        "error",
        [TimeoutError("read timed out"), _HttpStatusError(429), _HttpStatusError(503)],
    )
    async def test_temporary_failure_is_retried(
        self, logger: Logger, error: Exception
    ) -> None:
        download = AsyncMock(side_effect=[error, _skill_file("pdf")])

        skill, _ = await load_skill(
            content_service=_content_service(download),
            reference=_reference(updated_at=None),
            logger=logger,
        )

        assert skill is not None and skill.name == "pdf"
        assert download.await_count == 2

    @pytest.mark.parametrize("status_code", [403, 404])
    async def test_client_error_is_not_retried(
        self, logger: Logger, status_code: int
    ) -> None:
        download = AsyncMock(side_effect=_HttpStatusError(status_code))

        with pytest.raises(_HttpStatusError):
            await load_skill(
                content_service=_content_service(download),
                reference=_reference(updated_at=None),
                logger=logger,
            )

        download.assert_awaited_once()

    async def test_download_gives_up_after_the_last_attempt(
        self, logger: Logger
    ) -> None:
        download = AsyncMock(side_effect=TimeoutError("read timed out"))

        with pytest.raises(TimeoutError):
            await load_skill(
                content_service=_content_service(download),
                reference=_reference(updated_at=None),
                logger=logger,
            )

        assert download.await_count == SKILL_DOWNLOAD_ATTEMPTS

    async def test_oversized_file_is_skipped(self, logger: Logger) -> None:
        download = AsyncMock(return_value=b"x" * (MAX_SKILL_FILE_BYTES + 1))

        skill, _ = await load_skill(
            content_service=_content_service(download),
            reference=_reference(updated_at=None),
            logger=logger,
        )

        assert skill is None

    async def test_file_that_is_not_utf8_is_skipped(self, logger: Logger) -> None:
        download = AsyncMock(return_value=b"\xff\xfe\x00bad")

        skill, _ = await load_skill(
            content_service=_content_service(download),
            reference=_reference(updated_at=None),
            logger=logger,
        )

        assert skill is None

    async def test_downloads_across_turns_never_exceed_the_shared_limit(
        self, logger: Logger
    ) -> None:
        running = 0
        peak = 0

        async def tracked_download(*, content_id: str, **_: object) -> bytes:
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            running -= 1
            return _skill_file(f"skill-{content_id}")

        def turn() -> asyncio.Future[dict[str, SkillDefinition]]:
            return asyncio.ensure_future(
                load_selectable_skills(
                    content_service=_content_service(
                        AsyncMock(side_effect=tracked_download)
                    ),
                    selectable_skills=[
                        _reference(str(index), updated_at=None) for index in range(40)
                    ],
                    logger=logger,
                )
            )

        registries = await asyncio.gather(turn(), turn(), turn())

        assert all(len(registry) == 40 for registry in registries)
        assert peak == MAX_PARALLEL_SKILL_DOWNLOADS


class TestLoadSelectableSkillsSummary:
    async def test_one_failed_download_does_not_drop_the_other_skills(
        self, logger: Logger
    ) -> None:
        async def download(*, content_id: str, **_: object) -> bytes:
            if content_id == "broken":
                raise _HttpStatusError(404)
            return _skill_file(content_id)

        registry = await load_selectable_skills(
            content_service=_content_service(AsyncMock(side_effect=download)),
            selectable_skills=[
                _reference("alpha", name="alpha"),
                _reference("broken", name="broken"),
                _reference("beta", name="beta"),
            ],
            logger=logger,
        )

        assert sorted(registry) == ["alpha", "beta"]

    async def test_summary_counts_cached_downloaded_and_failed_skills(
        self, logger: Logger
    ) -> None:
        async def download(*, content_id: str, **_: object) -> bytes:
            if content_id == "broken":
                raise _HttpStatusError(404)
            return _skill_file(content_id)

        content_service = _content_service(AsyncMock(side_effect=download))
        await load_selectable_skills(
            content_service=content_service,
            selectable_skills=[_reference("alpha", name="alpha")],
            logger=logger,
        )

        await load_selectable_skills(
            content_service=content_service,
            selectable_skills=[
                _reference("alpha", name="alpha"),
                _reference("beta", name="beta"),
                _reference("broken", name="broken"),
            ],
            logger=logger,
        )

        logger.info.assert_called_with(  # type: ignore[attr-defined]
            "Loaded %d skill(s) from selectable_skills "
            "(listed=%d, from_cache=%d, downloaded=%d, failed=%d).",
            2,
            3,
            1,
            1,
            1,
        )
