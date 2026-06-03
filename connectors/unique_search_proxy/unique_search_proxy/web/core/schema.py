from __future__ import annotations

from enum import StrEnum
from typing import Any, overload

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

camelized_model_config = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


class ProxyErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FORBIDDEN_TARGET = "FORBIDDEN_TARGET"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    ENGINE_NOT_CONFIGURED = "ENGINE_NOT_CONFIGURED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    EMPTY_SEARCH_RESULTS = "EMPTY_SEARCH_RESULTS"


class ErrorDetail(BaseModel):
    model_config = camelized_model_config

    code: str
    message: str
    engine: str | None = None
    crawler: str | None = None
    retryable: bool = False
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    model_config = camelized_model_config

    error: ErrorDetail


class WebSearchResult(BaseModel):
    """Normalized search result used on the curated response path."""

    model_config = camelized_model_config

    url: str
    title: str
    snippet: str = Field(
        ...,
        description="A short description of the content found on this website",
    )
    content: str = Field(
        default="",
        description="The content of the website",
    )


class WebSearchResults(BaseModel):
    model_config = camelized_model_config
    results: list[WebSearchResult]

    def __len__(self) -> int:
        return len(self.results)

    @overload
    def extend(self, other: WebSearchResults) -> WebSearchResults: ...
    @overload
    def extend(self, other: list[WebSearchResult]) -> WebSearchResults: ...

    def extend(
        self, other: WebSearchResults | list[WebSearchResult]
    ) -> WebSearchResults:
        if isinstance(other, WebSearchResults):
            return WebSearchResults(results=self.results + other.results)
        elif isinstance(other, list):
            return WebSearchResults(results=self.results + other)
        else:
            raise ValueError(f"Invalid type: {type(other)}")

    def dedupe(self) -> WebSearchResults:
        """Drop duplicate results with the same URL string."""
        seen: set[str] = set()
        deduped: list[WebSearchResult] = []
        for result in self.results:
            if result.url in seen:
                continue
            seen.add(result.url)
            deduped.append(result)
        return WebSearchResults(results=deduped)


class SearchEngineRaw(BaseModel):
    model_config = camelized_model_config
    pages: list[dict]

    def append(self, page: dict) -> None:
        self.pages.append(page)


class ProviderConfigBase(BaseModel):
    """Base config for engines and crawlers."""

    model_config = camelized_model_config

    exposed_fields: list[str] = Field(
        default_factory=list,
        description="Call-schema fields exposed to LLM-driven callers",
    )


class PerUrlError(BaseModel):
    model_config = camelized_model_config

    code: str
    message: str


class CrawlUrlResult(BaseModel):
    model_config = camelized_model_config

    url: str
    content: str | None = Field(
        default=None,
        description="Markdown extracted from HTML responses; null when unprocessed",
    )
    content_type: str | None = Field(
        default=None,
        description="Response Content-Type (media type only, parameters stripped)",
    )
    error: PerUrlError | None = None
    raw: Any | None = Field(
        default=None,
        description="Unmodified response body text, or null when no body was received",
    )


class CrawlerConfig(ProviderConfigBase):
    crawler: str = Field(..., description="Crawler identifier")
