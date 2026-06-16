from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.projection import build_crawl_request_model

TavilyExtractDepth = Literal["basic", "advanced"]
TavilyExtractFormat = Literal["markdown", "text"]


class TavilyConfig(BaseCrawlerConfig[CrawlerType.TAVILY]):
    """Deployment config for the Tavily Extract crawler."""

    crawler: Literal[CrawlerType.TAVILY] = CrawlerType.TAVILY

    extract_depth: TavilyExtractDepth = Field(
        default="advanced",
        title="Extract depth",
        description=(
            "Tavily extract depth: `basic` or `advanced`. Advanced retrieves more "
            "data (tables, embedded content) with higher success."
        ),
    )
    format: TavilyExtractFormat = Field(
        default="markdown",
        title="Output format",
        description="Extracted content format: `markdown` or `text`.",
    )
    query: str | None = Field(
        default=None,
        title="Rerank query",
        description=(
            "User intent for reranking extracted content chunks. When set, "
            "`chunks_per_source` may be used."
        ),
    )
    chunks_per_source: int | None = Field(
        default=None,
        ge=1,
        le=5,
        title="Chunks per source",
        description=(
            "Max relevant chunks per URL when `query` is set (1–5). "
            "Chunks appear in `raw_content` separated by `[...]`."
        ),
    )
    include_images: bool = Field(
        default=False,
        title="Include images",
        description="Include extracted image URLs in the Tavily response.",
    )
    include_favicon: bool = Field(
        default=False,
        title="Include favicon",
        description="Include the favicon URL for each extracted result.",
    )
    include_usage: bool = Field(
        default=False,
        title="Include usage",
        description="Include Tavily credit usage information in the response.",
    )

    @model_validator(mode="after")
    def _chunks_per_source_requires_query(self) -> TavilyConfig:
        if self.chunks_per_source is not None and not self.query:
            raise ValueError("chunks_per_source requires query to be set")
        return self


TavilyCrawlRequest = build_crawl_request_model(TavilyConfig)


__all__ = [
    "TavilyConfig",
    "TavilyCrawlRequest",
    "TavilyExtractDepth",
    "TavilyExtractFormat",
]
