from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from unique_search_proxy.web.core.crawlers.config_types import CrawlerConfigTypes
from unique_search_proxy.web.core.schema import (
    CrawlUrlResult,
    PerUrlError,
    WebSearchResult,
    camelized_model_config,
)
from unique_search_proxy.web.core.search_engines import SearchEngineConfigTypes


class SearchRequest(BaseModel):
    model_config = camelized_model_config

    config: SearchEngineConfigTypes = Field(discriminator="engine")
    call: dict[str, Any] = Field(
        ...,
        description=(
            "Per-invocation parameters merged over config defaults "
            "(must include query; may include LLM-exposed fields)"
        ),
    )
    include_content: bool = Field(
        default=False,
        description="When true and the engine is snippet-only, crawl to fill content",
    )
    crawler_config: CrawlerConfigTypes | None = None
    timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Request timeout in seconds",
    )


class SearchResponse(BaseModel):
    model_config = camelized_model_config

    engine: str
    query: str
    raw: Any = Field(..., description="Opaque provider payload")
    curated: list[WebSearchResult]


class SearchCallSchemaRequest(BaseModel):
    model_config = camelized_model_config

    config: SearchEngineConfigTypes = Field(
        discriminator="engine",
        description="Deployment search-engine config used to project the call schema",
    )


class SearchCallSchemaResponse(BaseModel):
    model_config = camelized_model_config

    engine: str = Field(..., description="Search engine id from config")
    mode: str = Field(
        ...,
        description="Engine mode (e.g. standard) for observability and tooling",
    )
    snippet_only: bool = Field(
        ...,
        description=(
            "When true, search hits are snippet-only; includeContent requires crawlerConfig"
        ),
    )
    call_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for SearchRequest.call for this config",
    )


__all__ = [
    "CrawlRequest",
    "CrawlResponse",
    "CrawlUrlResult",
    "PerUrlError",
    "SearchCallSchemaRequest",
    "SearchCallSchemaResponse",
    "SearchRequest",
    "SearchResponse",
]


class CrawlRequest(BaseModel):
    model_config = camelized_model_config

    urls: list[str] = Field(..., min_length=1, description="URLs to crawl")
    config: CrawlerConfigTypes
    accepted_content_types: list[str] | None = Field(
        default=None,
        description=(
            "Optional hint for callers (e.g. text/html). The proxy does not filter "
            "on this; consumers decide how to handle each result's contentType."
        ),
    )
    parallel: bool = Field(
        default=True,
        description="Whether to crawl URLs concurrently",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Per-request timeout in seconds",
    )


class CrawlResponse(BaseModel):
    model_config = camelized_model_config

    crawler: str
    results: list[CrawlUrlResult]
