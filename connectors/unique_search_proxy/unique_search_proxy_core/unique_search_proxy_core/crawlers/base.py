from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from pydantic import BaseModel, Field

from unique_search_proxy_core.param_policy.derive import derive_request_model
from unique_search_proxy_core.param_policy.request_base import CrawlRequestBase
from unique_search_proxy_core.schema import CrawlUrlResult, deployment_model_config

if TYPE_CHECKING:
    from httpx import AsyncClient

CrawlerTypeT = TypeVar("CrawlerTypeT", bound="CrawlerType")
CrawlerRequestT = TypeVar("CrawlerRequestT", bound=BaseModel)


class CrawlerType(StrEnum):
    """Registered crawler ids (JSON discriminator values)."""

    BASIC = "Basic"
    TAVILY = "Tavily"
    JINA = "Jina"
    FIRECRAWL = "Firecrawl"


class BaseCrawlerConfig(BaseModel, Generic[CrawlerTypeT]):
    """Deployment config for a crawler; each crawler narrows ``crawler`` with a Literal."""

    model_config = deployment_model_config

    #: Name of the derived request model; set by every concrete crawler config.
    _request_model_name: ClassVar[str]

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """HTTP request body model, cached per config class.

        :class:`CrawlRequestBase` (required ``urls``) + this config's fields.

        Example: ``BasicConfig.request_model()`` -> ``BasicCrawlRequest``.
        """
        return derive_request_model(
            cls,
            base=CrawlRequestBase,
            name=cls._request_model_name,
        )

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
        """Crawl URLs from a derived request model (``BasicCrawlRequest``, …)."""
