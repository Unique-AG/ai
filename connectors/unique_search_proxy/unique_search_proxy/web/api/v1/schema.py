from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from unique_search_proxy.web.core.schema import (
    CrawlerConfig,
    SearchEngineConfig,
    WebSearchResult,
    camelized_model_config,
)


class SearchRequest(BaseModel):
    model_config = camelized_model_config

    query: str = Field(..., min_length=1, description="Search query string")
    config: SearchEngineConfig
    fetch_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Number of results to fetch",
    )
    include_content: bool = Field(
        default=False,
        description="When true and the engine is snippet-only, crawl to fill content",
    )
    crawler_config: CrawlerConfig | None = None
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


class PerUrlError(BaseModel):
    model_config = camelized_model_config

    code: str
    message: str


class CrawlUrlResult(BaseModel):
    model_config = camelized_model_config

    url: str
    content: str | None = None
    error: PerUrlError | None = None
    raw: Any | None = Field(
        default=None,
        description="Opaque fetched payload, or null when fetch failed",
    )


class CrawlRequest(BaseModel):
    model_config = camelized_model_config

    urls: list[str] = Field(..., min_length=1, description="URLs to crawl")
    config: CrawlerConfig
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
