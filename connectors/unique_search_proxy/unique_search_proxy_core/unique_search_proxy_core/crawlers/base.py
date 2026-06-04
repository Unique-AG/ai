from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar

from unique_search_proxy_core.schema import CrawlUrlResult, ProviderConfigBase

if TYPE_CHECKING:
    from httpx import AsyncClient

CrawlerTypeT = TypeVar("CrawlerTypeT", bound="CrawlerType")
CrawlerConfigT = TypeVar("CrawlerConfigT", bound="BaseCrawlerConfig")


class CrawlerType(StrEnum):
    """Registered crawler ids (JSON discriminator values)."""

    BASIC = "basic"


class BaseCrawlerConfig(ProviderConfigBase, Generic[CrawlerTypeT]):
    """Shared crawler config; each crawler narrows ``crawler`` with a Literal."""

    crawler: CrawlerTypeT


class BaseCrawler(ABC, Generic[CrawlerConfigT]):
    """Crawler contract: per-URL outcomes with optional url-safety enforcement."""

    crawler_id: str

    def __init__(
        self,
        config: CrawlerConfigT,
        *,
        http_client: AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._http_client = http_client

    @abstractmethod
    async def crawl(self, urls: list[str], *, timeout: int) -> list[CrawlUrlResult]:
        """Crawl URLs and return per-URL results (partial success)."""
