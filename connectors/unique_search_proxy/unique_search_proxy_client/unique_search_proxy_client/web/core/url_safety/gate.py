from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from unique_search_proxy_core.schema import CrawlUrlResult
from unique_search_proxy_core.url_safety import (
    ResolvedCrawlTarget,
    UrlSafetyOutcome,
    UrlSafetyService,
)

from unique_search_proxy_client.web.core.provider_response import (
    crawl_deadline_missed,
    crawl_forbidden_target,
)
from unique_search_proxy_client.web.monitoring.metrics import record_crawl_blocked

if TYPE_CHECKING:
    from httpx import AsyncClient

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AllowedCrawlTarget:
    """User-facing URL paired with the validated resolution for pinned egress."""

    display_url: str
    resolved: ResolvedCrawlTarget


@dataclass(frozen=True)
class UrlSafetyGateResult:
    allowed_targets: list[AllowedCrawlTarget]
    blocked_by_index: dict[int, CrawlUrlResult]
    timed_out_by_index: dict[int, CrawlUrlResult] = field(default_factory=dict)

    @property
    def uncrawled_by_index(self) -> dict[int, CrawlUrlResult]:
        return {**self.blocked_by_index, **self.timed_out_by_index}


async def apply_url_safety_gate(
    urls: list[str],
    *,
    redirect_http_client: AsyncClient,
    deadline: float | None = None,
) -> UrlSafetyGateResult:
    """Partition crawl URLs into allowed, blocked and timed-out targets."""
    allowed_targets: list[AllowedCrawlTarget] = []
    blocked_by_index: dict[int, CrawlUrlResult] = {}
    timed_out_by_index: dict[int, CrawlUrlResult] = {}

    for index, url in enumerate(urls):
        outcome = await _validate_before_deadline(
            url,
            redirect_http_client=redirect_http_client,
            deadline=deadline,
        )
        if outcome is None:
            timed_out_by_index = {
                unchecked_index: crawl_deadline_missed(
                    unchecked_url.strip(),
                    "URL safety check did not finish before the crawl deadline",
                )
                for unchecked_index, unchecked_url in enumerate(
                    urls[index:],
                    start=index,
                )
            }
            _LOGGER.warning(
                "URL safety checks missed the crawl deadline unchecked=%d",
                len(timed_out_by_index),
            )
            break

        if outcome.blocked is not None:
            record_crawl_blocked(outcome.blocked.category)
            blocked_by_index[index] = crawl_forbidden_target(
                outcome.url.strip(),
                outcome.blocked.reason,
            )
            continue

        if outcome.resolved is None:
            msg = "URL safety allowed a crawl target without resolved metadata"
            raise RuntimeError(msg)

        allowed_targets.append(
            AllowedCrawlTarget(
                display_url=outcome.url.strip(),
                resolved=outcome.resolved,
            ),
        )

    return UrlSafetyGateResult(
        allowed_targets=allowed_targets,
        blocked_by_index=blocked_by_index,
        timed_out_by_index=timed_out_by_index,
    )


async def _validate_before_deadline(
    url: str,
    *,
    redirect_http_client: AsyncClient,
    deadline: float | None,
) -> UrlSafetyOutcome | None:
    """Return the URL's safety outcome, or ``None`` when the deadline passes first."""
    try:
        async with asyncio.timeout_at(deadline):
            [outcome] = await UrlSafetyService.validate_urls_individually(
                [url],
                redirect_http_client=redirect_http_client,
            )
    except TimeoutError:
        return None
    return outcome


def merge_crawl_results(
    urls: list[str],
    *,
    uncrawled_by_index: dict[int, CrawlUrlResult],
    crawler_results: list[CrawlUrlResult],
) -> list[CrawlUrlResult]:
    """Merge the gate's results for uncrawled URLs with crawler outcomes in order."""
    merged: list[CrawlUrlResult] = []
    crawler_index = 0
    for index, _url in enumerate(urls):
        uncrawled = uncrawled_by_index.get(index)
        if uncrawled is not None:
            merged.append(uncrawled)
            continue

        merged.append(crawler_results[crawler_index])
        crawler_index += 1

    return merged
