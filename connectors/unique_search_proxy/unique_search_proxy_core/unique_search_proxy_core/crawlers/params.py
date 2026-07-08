"""Crawler request merge helpers (no HTTP)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from unique_search_proxy_core.crawlers.config_types import crawler_config_from_request
from unique_search_proxy_core.param_policy import URLS_FIELD
from unique_search_proxy_core.param_policy.resolver import ConfigRequestResolver

CRAWLER_FIELD = "crawler"
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
    request_model = ConfigRequestResolver.crawl_request_model(type(config))
    defaults = crawler_config_defaults(config)
    merged: dict[str, Any] = {**defaults, **invocation}
    merged[CRAWLER_FIELD] = getattr(config, CRAWLER_FIELD)
    request = request_model.model_validate(merged)
    crawler_config_from_request(request)
    return request


__all__ = [
    "CRAWLER_FIELD",
    "TIMEOUT_FIELD",
    "URLS_FIELD",
    "crawler_config_defaults",
    "merge_crawler_config_and_invocation",
]
