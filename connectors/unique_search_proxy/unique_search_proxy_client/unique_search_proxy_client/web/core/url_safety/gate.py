from __future__ import annotations

from dataclasses import dataclass

from unique_search_proxy_core.schema import CrawlUrlResult
from unique_search_proxy_core.url_safety import ResolvedCrawlTarget, UrlSafetyService

from unique_search_proxy_client.web.core.provider_response import crawl_forbidden_target
from unique_search_proxy_client.web.monitoring.metrics import record_crawl_blocked


@dataclass(frozen=True)
class AllowedCrawlTarget:
    """User-facing URL paired with the validated resolution for pinned egress."""

    display_url: str
    resolved: ResolvedCrawlTarget


@dataclass(frozen=True)
class UrlSafetyGateResult:
    allowed_targets: list[AllowedCrawlTarget]
    blocked_by_index: dict[int, CrawlUrlResult]


async def apply_url_safety_gate(urls: list[str]) -> UrlSafetyGateResult:
    """Validate crawl URLs and partition them into allowed vs blocked targets."""
    outcomes = await UrlSafetyService.validate_urls_individually(urls)
    allowed_targets: list[AllowedCrawlTarget] = []
    blocked_by_index: dict[int, CrawlUrlResult] = {}

    for index, outcome in enumerate(outcomes):
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
    )


def merge_crawl_results(
    urls: list[str],
    *,
    blocked_by_index: dict[int, CrawlUrlResult],
    crawler_results: list[CrawlUrlResult],
) -> list[CrawlUrlResult]:
    """Merge per-URL blocked results with crawler outcomes in request order."""
    merged: list[CrawlUrlResult] = []
    crawler_index = 0
    for index, _url in enumerate(urls):
        blocked = blocked_by_index.get(index)
        if blocked is not None:
            merged.append(blocked)
            continue

        merged.append(crawler_results[crawler_index])
        crawler_index += 1

    return merged
