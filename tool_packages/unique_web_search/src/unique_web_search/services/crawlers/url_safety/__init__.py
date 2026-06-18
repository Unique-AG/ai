"""Deprecated re-exports — use ``unique_search_proxy_core.url_safety`` directly."""

from unique_search_proxy_core.url_safety import (
    BlockedCrawlTarget,
    CrawlTargetValidationError,
    ResolvedCrawlTarget,
    UrlSafetyOutcome,
    UrlSafetyService,
    UrlSafetySettings,
    url_safety_settings,
)

__all__ = [
    "BlockedCrawlTarget",
    "CrawlTargetValidationError",
    "ResolvedCrawlTarget",
    "UrlSafetyOutcome",
    "UrlSafetyService",
    "UrlSafetySettings",
    "url_safety_settings",
]
