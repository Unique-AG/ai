from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import BaseModel, Field

from unique_search_proxy_core.schema import CrawlUrlResult, camelized_model_config

if TYPE_CHECKING:
    from httpx import AsyncClient

CrawlerTypeT = TypeVar("CrawlerTypeT", bound="CrawlerType")
CrawlerRequestT = TypeVar("CrawlerRequestT", bound=BaseModel)


class CrawlerType(StrEnum):
    """Registered crawler ids (JSON discriminator values)."""

    BASIC = "BasicCrawler"


class BaseCrawlerConfig(BaseModel, Generic[CrawlerTypeT]):
    """Shared crawler config; each crawler narrows ``crawler`` with a Literal."""

    model_config = camelized_model_config

    crawler: CrawlerTypeT
    timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Request timeout in seconds",
    )


class BaseCrawler(ABC, Generic[CrawlerRequestT]):
    """Crawler contract: per-URL outcomes with optional url-safety enforcement."""

    crawler_id: str

    def __init__(
        self,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        self._http_client = http_client

    @abstractmethod
    async def crawl(self, request: CrawlerRequestT) -> list[CrawlUrlResult]:
        """Crawl URLs from a flat request model (``BasicCrawlerRequest``, …)."""
