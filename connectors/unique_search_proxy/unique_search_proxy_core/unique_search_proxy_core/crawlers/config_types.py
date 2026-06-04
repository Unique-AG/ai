from __future__ import annotations

from typing import Annotated, Any, TypeAlias, Union

from pydantic import BaseModel, Field, TypeAdapter

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerConfig
from unique_search_proxy_core.projection import URLS_FIELD, build_crawl_request_model

CrawlerConfigTypes: TypeAlias = BasicCrawlerConfig

CRAWLER_NAME_TO_CONFIG: dict[str, type[BaseCrawlerConfig]] = {
    CrawlerType.BASIC.value: BasicCrawlerConfig,
}

_crawler_config_adapter: TypeAdapter[CrawlerConfigTypes] = TypeAdapter(
    CrawlerConfigTypes,
)

_CRAWL_REQUEST_EXCLUDED_FIELDS = {URLS_FIELD}


def parse_crawler_config(data: object) -> CrawlerConfigTypes:
    return _crawler_config_adapter.validate_python(data)


def build_crawl_request_union() -> Any:
    """Discriminated union of flat ``POST /v1/crawl`` bodies (``crawler_type`` discriminator)."""
    members = tuple(CRAWLER_NAME_TO_CONFIG.values())
    request_models = tuple(
        build_crawl_request_model(config_cls) for config_cls in members
    )
    if len(request_models) == 1:
        return request_models[0]
    return Annotated[
        Union[request_models],  # type: ignore[valid-type]
        Field(discriminator="crawler_type"),
    ]


CrawlRequestTypes = build_crawl_request_union()
CrawlRequest = CrawlRequestTypes

_crawl_request_adapter: TypeAdapter[BaseModel] = TypeAdapter(CrawlRequestTypes)  # type: ignore[arg-type]


def parse_crawl_request(data: object) -> BaseModel:
    return _crawl_request_adapter.validate_python(data)


def crawler_config_from_request(request: BaseModel) -> CrawlerConfigTypes:
    """Rebuild deployment config from a flat crawl request (excludes ``urls`` only)."""
    crawler_id = getattr(request, "crawler_type", None)
    if not isinstance(crawler_id, str):
        raise ValueError("Flat crawl request is missing crawler_type discriminator")

    config_cls = CRAWLER_NAME_TO_CONFIG.get(crawler_id.lower())
    if config_cls is None:
        raise ValueError(f"No crawler config registered for {crawler_id!r}")

    payload = request.model_dump(
        exclude=_CRAWL_REQUEST_EXCLUDED_FIELDS,
        mode="python",
    )
    return parse_crawler_config(payload)
