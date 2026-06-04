"""LLM-facing call JSON Schema derived from crawler deployment config (no HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from unique_search_proxy_core.crawlers.basic.schema import (
    BasicCrawlerCall,
    BasicCrawlerConfig,
)
from unique_search_proxy_core.crawlers.config_types import (
    CRAWLER_NAME_TO_CONFIG,
    CrawlerConfigTypes,
    parse_crawler_config,
)
from unique_search_proxy_core.projection import project_call_schema
from unique_search_proxy_core.providers.schema import provider_default_config


@dataclass(frozen=True)
class CrawlCallSchemaDescriptor:
    """Metadata and JSON Schema for the crawler call model on ``POST /v1/crawl``."""

    crawler: str
    call_schema: dict[str, Any]


def _llm_call_schema_for_config(config: CrawlerConfigTypes) -> type[BaseModel]:
    if isinstance(config, BasicCrawlerConfig):
        exposed = list(dict.fromkeys(["urls", *config.exposed_fields]))
        return project_call_schema(BasicCrawlerCall, exposed)
    raise ValueError(f"No LLM call schema for crawler config {type(config).__name__}")


def resolve_crawl_call_schema_from_config(
    crawler_id: str,
    config: CrawlerConfigTypes,
) -> CrawlCallSchemaDescriptor:
    """Project the LLM-visible call surface from a parsed deployment config."""
    config_cls = CRAWLER_NAME_TO_CONFIG[crawler_id.lower()]
    if type(config) is not config_cls:
        raise ValueError(
            f"Config type {type(config).__name__} does not match crawler {crawler_id!r}",
        )
    projected = _llm_call_schema_for_config(config)
    return CrawlCallSchemaDescriptor(
        crawler=crawler_id.lower(),
        call_schema=projected.model_json_schema(),
    )


def resolve_crawl_call_schema(
    crawler_id: str,
    *,
    config: CrawlerConfigTypes | dict[str, Any] | None = None,
) -> CrawlCallSchemaDescriptor:
    """Resolve call schema from deployment config or crawler defaults."""
    if config is not None:
        parsed = (
            config if isinstance(config, BaseModel) else parse_crawler_config(config)
        )
        return resolve_crawl_call_schema_from_config(crawler_id, parsed)

    defaults = provider_default_config("crawler", crawler_id)
    parsed = parse_crawler_config(defaults)
    return resolve_crawl_call_schema_from_config(crawler_id, parsed)


__all__ = [
    "CrawlCallSchemaDescriptor",
    "resolve_crawl_call_schema",
    "resolve_crawl_call_schema_from_config",
]
