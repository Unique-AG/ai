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


BasicCrawlRequest = BasicConfig.request_model()


__all__ = [
    "BasicConfig",
    "BasicCrawlRequest",
]
