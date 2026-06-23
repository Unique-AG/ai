from __future__ import annotations

from typing import Annotated, Any, TypeAlias, Union

from pydantic import BaseModel, Field, TypeAdapter

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import (
    BasicConfig,
    BasicCrawlRequest,
)
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlConfig,
    FirecrawlCrawlRequest,
)
from unique_search_proxy_core.crawlers.jina.schema import JinaConfig, JinaCrawlRequest
from unique_search_proxy_core.crawlers.projection import (
    URLS_FIELD,
    build_crawl_request_model,
)
from unique_search_proxy_core.crawlers.tavily.schema import (
    TavilyConfig,
    TavilyCrawlRequest,
)

CrawlerConfigTypes: TypeAlias = (
    BasicConfig | TavilyConfig | JinaConfig | FirecrawlConfig
)

CRAWLER_NAME_TO_CONFIG: dict[str, type[BaseCrawlerConfig]] = {
    CrawlerType.BASIC.value: BasicConfig,
    CrawlerType.TAVILY.value: TavilyConfig,
    CrawlerType.JINA.value: JinaConfig,
    CrawlerType.FIRECRAWL.value: FirecrawlConfig,
}

_crawler_config_adapter: TypeAdapter[CrawlerConfigTypes] = TypeAdapter(
    CrawlerConfigTypes,
)


def parse_crawler_config(data: object) -> CrawlerConfigTypes:
    return _crawler_config_adapter.validate_python(data)


def build_crawl_request_union() -> Any:
    """Discriminated union of flat ``POST /v1/crawl`` bodies (``crawler`` discriminator)."""
    members = tuple(CRAWLER_NAME_TO_CONFIG.values())
    request_models = tuple(
        build_crawl_request_model(config_cls) for config_cls in members
    )
    if len(request_models) == 1:
        return request_models[0]
    return Annotated[
        Union[request_models],  # type: ignore[valid-type]
        Field(discriminator="crawler"),
    ]


CrawlRequestTypes = build_crawl_request_union()
CrawlRequest = CrawlRequestTypes

_crawl_request_adapter: TypeAdapter[BaseModel] = TypeAdapter(CrawlRequestTypes)  # type: ignore[arg-type]


def parse_crawl_request(data: object) -> BaseModel:
    request = _crawl_request_adapter.validate_python(data)
    crawler_config_from_request(request)
    return request


def crawler_config_from_request(request: BaseModel) -> CrawlerConfigTypes:
    """Rebuild deployment config from a flat crawl request (excludes ``urls``)."""
    crawler_id = getattr(request, "crawler", None)
    if not isinstance(crawler_id, str):
        raise ValueError("Flat crawl request is missing crawler discriminator")

    config_cls = CRAWLER_NAME_TO_CONFIG.get(crawler_id)
    if config_cls is None:
        raise ValueError(f"No crawler config registered for {crawler_id!r}")

    payload = request.model_dump(exclude={URLS_FIELD}, mode="python")
    return parse_crawler_config(payload)


__all__ = [
    "BasicConfig",
    "BasicCrawlRequest",
    "CRAWLER_NAME_TO_CONFIG",
    "CrawlRequest",
    "CrawlRequestTypes",
    "CrawlerConfigTypes",
    "FirecrawlConfig",
    "FirecrawlCrawlRequest",
    "JinaConfig",
    "JinaCrawlRequest",
    "TavilyConfig",
    "TavilyCrawlRequest",
    "build_crawl_request_union",
    "crawler_config_from_request",
    "parse_crawl_request",
    "parse_crawler_config",
]
