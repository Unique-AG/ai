from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from unique_search_proxy.web.core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy.web.core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)


class BasicCrawlerCall(BaseModel):
    """LLM-facing call surface for the basic crawler (urls supplied per invocation)."""

    urls: list[str] = Field(
        ...,
        min_length=1,
        description="URLs to fetch and convert to markdown",
    )


class BasicCrawlerConfig(BaseCrawlerConfig[CrawlerType.BASIC]):
    """Deployment config for the HTTP basic crawler."""

    crawler: Literal[CrawlerType.BASIC] = CrawlerType.BASIC

    content_type_handlers: dict[str, ContentTypeHandlerPolicy] = Field(
        default_factory=dict,
        description=(
            "Per media-type policy using exact Content-Type values (no parameters). "
            "allow: run the built-in processor into ``content``; "
            "forbid: return ``raw`` only. Types not listed are not processed."
        ),
        examples=[
            {
                "text/html": "allow",
                "application/xhtml+xml": "allow",
                "application/pdf": "forbid",
            },
        ],
    )
    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent HTTP fetches",
    )
    exposed_fields: list[str] = Field(
        default_factory=list,
        description="Call-schema fields exposed to LLM-driven callers (urls always exposed)",
    )
