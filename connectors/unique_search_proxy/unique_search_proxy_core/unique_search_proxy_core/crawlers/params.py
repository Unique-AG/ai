"""Crawler request merge helpers (no HTTP)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

CRAWLER_FIELD = "crawler"
URLS_FIELD = "urls"
TIMEOUT_FIELD = "timeout"

_DEPLOYMENT_DEFAULT_EXCLUDED_FIELDS = frozenset({CRAWLER_FIELD, URLS_FIELD})


def crawler_config_defaults(config: BaseModel) -> dict[str, Any]:
    """Deployment defaults merged into each flat crawl request."""
    defaults: dict[str, Any] = {}
    for field_name in type(config).model_fields:
        if field_name in _DEPLOYMENT_DEFAULT_EXCLUDED_FIELDS:
            continue
        defaults[field_name] = getattr(config, field_name)
    return defaults


def merge_crawler_config_and_invocation(
    config: BaseModel,
    invocation: dict[str, Any],
) -> BaseModel:
    """Merge deployment config defaults with caller/LLM args into a flat crawl request."""
    defaults = crawler_config_defaults(config)
    merged: dict[str, Any] = {**defaults, **invocation}
    merged[CRAWLER_FIELD] = getattr(config, CRAWLER_FIELD)
    return type(config).model_validate(merged)


__all__ = [
    "CRAWLER_FIELD",
    "TIMEOUT_FIELD",
    "URLS_FIELD",
    "crawler_config_defaults",
    "merge_crawler_config_and_invocation",
]
