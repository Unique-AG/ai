from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import Field, model_validator
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.schema import DeactivatedNone

TavilyExtractDepth = Literal["basic", "advanced"]
TavilyExtractFormat = Literal["markdown", "text"]

StrOrNone: TypeAlias = Annotated[str, Field(title="String")] | DeactivatedNone
ChunksPerSourceOrNone: TypeAlias = (
    Annotated[int, Field(title="Integer", ge=1, le=5)] | DeactivatedNone
)


class TavilyConfig(BaseCrawlerConfig[CrawlerType.TAVILY]):
    """Deployment config for the Tavily Extract crawler."""

    _request_model_name: ClassVar[str] = "TavilyCrawlRequest"

    crawler: Annotated[
        Literal[CrawlerType.TAVILY], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=CrawlerType.TAVILY,
        title="Crawler",
        description="Provider discriminator; must be `Tavily` for this config.",
    )

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
    query: StrOrNone = Field(
        default=None,
        title="Rerank query",
        description=(
            "User intent for reranking extracted content chunks. When set, "
            "`chunks_per_source` may be used."
        ),
    )
    chunks_per_source: ChunksPerSourceOrNone = Field(
        default=None,
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


TavilyCrawlRequest = TavilyConfig.request_model()


__all__ = [
    "TavilyConfig",
    "TavilyCrawlRequest",
    "TavilyExtractDepth",
    "TavilyExtractFormat",
]
