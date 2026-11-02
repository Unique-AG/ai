from __future__ import annotations

from typing import Annotated, ClassVar, Literal

from pydantic import Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.content_types import ContentTypeToggles


class BasicConfig(BaseCrawlerConfig[CrawlerType.BASIC]):
    """Deployment config for the HTTP basic crawler."""

    _request_model_name: ClassVar[str] = "BasicCrawlRequest"

    crawler: Annotated[
        Literal[CrawlerType.BASIC], RJSFMetaTag.SpecialWidget.hidden()
    ] = Field(
        default=CrawlerType.BASIC,
        title="Crawler",
        description="Provider discriminator; must be `Basic` for this config.",
    )

    content_types: ContentTypeToggles = Field(
        default_factory=ContentTypeToggles,
        title="Content types",
        description=(
            "Enable built-in processing per media type. "
            "Unchecked types return raw body only."
        ),
    )
    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=50,
        title="Maximum concurrent HTTP fetches",
        description="Maximum concurrent HTTP fetches",
    )
    max_pdf_bytes: int = Field(
        default=10 * 1024 * 1024,
        ge=1,
        title="Maximum PDF download size",
        description=(
            "Hard ceiling for a single PDF download in bytes. "
            "Bodies above this limit are rejected during streaming."
        ),
    )
    max_inline_pdf_bytes: int = Field(
        default=2 * 1024 * 1024,
        ge=1,
        title="Maximum inline PDF size",
        description=(
            "PDFs at or below this size are extracted inline. "
            "Larger admitted PDFs are held for download via /v1/document-holds."
        ),
    )
    max_pdf_pages: int = Field(
        default=50,
        ge=1,
        title="Maximum PDF pages",
        description="Maximum number of pages to extract into the crawl response",
    )
    max_pdf_page_chars: int = Field(
        default=20_000,
        ge=1,
        title="Maximum characters per PDF page",
        description="Per-page Markdown character cap during extraction",
    )
    max_pdf_document_chars: int = Field(
        default=100_000,
        ge=1,
        title="Maximum PDF document characters",
        description="Total Markdown character cap across extracted PDF pages",
    )


BasicCrawlRequest = BasicConfig.request_model()


__all__ = [
    "BasicConfig",
    "BasicCrawlRequest",
]
