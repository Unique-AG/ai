from __future__ import annotations

from enum import StrEnum
from typing import Any

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


class ProviderConfigBase(BaseModel):
    """Base config for engines and crawlers."""

    model_config = camelized_model_config

    exposed_fields: list[str] = Field(
        default_factory=list,
        description="Call-schema fields exposed to LLM-driven callers",
    )


class SearchEngineConfig(ProviderConfigBase):
    engine: str = Field(..., description="Search engine identifier")


class CrawlerConfig(ProviderConfigBase):
    crawler: str = Field(..., description="Crawler identifier")
