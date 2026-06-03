from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from unique_search_proxy.web.core.crawlers.config_types import CrawlerConfigTypes
from unique_search_proxy.web.core.projection import build_request_model
from unique_search_proxy.web.core.schema import (
    CrawlUrlResult,
    PerUrlError,
    WebSearchResult,
    camelized_model_config,
)
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig

# Derived flat request body; add union members when more engines register.
SearchRequest = build_request_model(GoogleConfig)


class SearchResponse(BaseModel):
    model_config = camelized_model_config

    engine: str
    query: str
    raw: Any = Field(..., description="Opaque provider payload")
    curated: list[WebSearchResult]


class ProvidersListResponse(BaseModel):
    model_config = camelized_model_config

    search_engines: list[str] = Field(
        ...,
        description="Registered search engine ids (config discriminator values)",
    )
    crawlers: list[str] = Field(
        ...,
        description="Registered crawler ids (config discriminator values)",
    )


class ProviderJsonSchemaResponse(BaseModel):
    model_config = camelized_model_config

    json_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for provider deployment configuration",
    )
    provider_id: str | None = Field(
        default=None,
        description="Set when the schema is for a single provider",
    )


class ProviderDefaultConfigResponse(BaseModel):
    model_config = camelized_model_config

    provider_id: str
    default_config: dict[str, Any] = Field(
        ...,
        description="Default deployment config (camelCase keys)",
    )


class SearchCallSchemaResponse(BaseModel):
    model_config = camelized_model_config

    engine: str = Field(..., description="Search engine id")
    mode: str = Field(
        ...,
        description="Engine mode (e.g. standard) for observability and tooling",
    )
    snippet_only: bool = Field(
        ...,
        description="When true, search hits are snippet-only; use POST /v1/crawl for bodies",
    )
    call_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for the engine call model on POST /v1/search",
    )


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


__all__ = [
    "CrawlRequest",
    "CrawlResponse",
    "CrawlUrlResult",
    "PerUrlError",
    "ProviderDefaultConfigResponse",
    "ProviderJsonSchemaResponse",
    "ProvidersListResponse",
    "SearchCallSchemaResponse",
    "SearchRequest",
    "SearchResponse",
]
