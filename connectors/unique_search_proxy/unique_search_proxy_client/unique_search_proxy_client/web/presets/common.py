"""Shared payload builders for search and crawl presets."""

from __future__ import annotations

from typing import Any

from unique_search_proxy_core.providers.schema import provider_default_config

DEFAULT_SEARCH_QUERY = "unique ag"
EXAMPLE_URLS = ["https://example.com"]
EXAMPLE_URLS_MULTI = [
    "https://example.com",
    "https://www.example.org",
]


def build_search_preset(
    engine: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a flat ``POST /v1/search`` body for the given engine."""
    payload: dict[str, Any] = {
        "engine": engine,
        "query": DEFAULT_SEARCH_QUERY,
        "fetchSize": 10,
        "timeout": 30,
    }
    if engine == "google":
        payload["safe"] = "active"
    if overrides:
        payload.update(overrides)
    return payload


def build_crawl_preset(
    crawler: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a flat ``POST /v1/crawl`` body starting from deployment defaults."""
    payload = provider_default_config("crawler", crawler)
    payload["urls"] = list(EXAMPLE_URLS)
    if overrides:
        payload.update(overrides)
    return payload


__all__ = [
    "DEFAULT_SEARCH_QUERY",
    "EXAMPLE_URLS",
    "EXAMPLE_URLS_MULTI",
    "build_crawl_preset",
    "build_search_preset",
]
