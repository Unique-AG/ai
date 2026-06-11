"""Crawler request merge helpers (no HTTP)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from unique_search_proxy_core.projection import build_crawl_request_model

CRAWLER_FIELD = "crawler"
URLS_FIELD = "urls"
TIMEOUT_FIELD = "timeout"


def crawler_config_defaults(config: BaseModel) -> dict[str, Any]:
    """Deployment defaults merged into each flat crawl request."""
    defaults: dict[str, Any] = {}
    for field_name in type(config).model_fields:
        if field_name == CRAWLER_FIELD:
            continue
        defaults[field_name] = getattr(config, field_name)
    return defaults


def merge_crawler_config_and_invocation(
    config: BaseModel,
    invocation: dict[str, Any],
) -> BaseModel:
    """Merge deployment config defaults with caller/LLM args into a flat crawl request."""
    request_model = build_crawl_request_model(type(config))
    defaults = crawler_config_defaults(config)
    merged: dict[str, Any] = {**defaults, **invocation}
    if CRAWLER_FIELD in request_model.model_fields:
        merged[CRAWLER_FIELD] = getattr(config, CRAWLER_FIELD)
    return request_model.model_validate(merged)


__all__ = [
    "CRAWLER_FIELD",
    "TIMEOUT_FIELD",
    "URLS_FIELD",
    "crawler_config_defaults",
    "merge_crawler_config_and_invocation",
]
