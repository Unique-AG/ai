from __future__ import annotations

from typing import Annotated, Any, TypeAlias, Union

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
from unique_search_proxy_core.crawlers.firecrawl.schema import (
    FirecrawlCrawlRequest,
)
from unique_search_proxy_core.crawlers.jina.schema import JinaCrawlRequest
from unique_search_proxy_core.crawlers.params import URLS_FIELD
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest

CrawlerConfigTypes: TypeAlias = (
    BasicCrawlRequest | TavilyCrawlRequest | JinaCrawlRequest | FirecrawlCrawlRequest
)

CRAWLER_NAME_TO_CONFIG: dict[str, type[BaseCrawlerConfig]] = {
    CrawlerType.BASIC.value: BasicCrawlRequest,
    CrawlerType.TAVILY.value: TavilyCrawlRequest,
    CrawlerType.JINA.value: JinaCrawlRequest,
    CrawlerType.FIRECRAWL.value: FirecrawlCrawlRequest,
}

_crawler_config_adapter: TypeAdapter[CrawlerConfigTypes] = TypeAdapter(
    CrawlerConfigTypes,
)

_CRAWL_REQUEST_EXCLUDED_FIELDS = {URLS_FIELD}


def parse_crawler_config(data: object) -> CrawlerConfigTypes:
    return _crawler_config_adapter.validate_python(data)


def build_crawl_request_union() -> Any:
    """Discriminated union of flat ``POST /v1/crawl`` bodies (``crawler`` discriminator)."""
    members = tuple(CRAWLER_NAME_TO_CONFIG.values())
    if len(members) == 1:
        return members[0]
    return Annotated[
        Union[members],  # type: ignore[valid-type]
        Field(discriminator="crawler"),
    ]


CrawlRequestTypes = build_crawl_request_union()
CrawlRequest = CrawlRequestTypes

_crawl_request_adapter: TypeAdapter[BaseModel] = TypeAdapter(CrawlRequestTypes)  # type: ignore[arg-type]


def parse_crawl_request(data: object) -> BaseModel:
    request = _crawl_request_adapter.validate_python(data)
    urls = getattr(request, URLS_FIELD, None)
    if not isinstance(urls, list) or len(urls) < 1:
        raise ValidationError.from_exception_data(
            title=type(request).__name__,
            line_errors=[
                {
                    "type": "too_short",
                    "loc": (URLS_FIELD,),
                    "msg": "List should have at least 1 item",
                    "input": urls,
                    "ctx": {"field_type": "List", "min_length": 1},
                },
            ],
        )
    return request


def crawler_config_from_request(request: BaseModel) -> CrawlerConfigTypes:
    """Rebuild deployment config from a flat crawl request (excludes ``urls`` only)."""
    crawler_id = getattr(request, "crawler", None)
    if not isinstance(crawler_id, str):
        raise ValueError("Flat crawl request is missing crawler discriminator")

    config_cls = CRAWLER_NAME_TO_CONFIG.get(crawler_id)
    if config_cls is None:
        raise ValueError(f"No crawler config registered for {crawler_id!r}")

    payload = request.model_dump(
        exclude=_CRAWL_REQUEST_EXCLUDED_FIELDS,
        mode="python",
    )
    return parse_crawler_config(payload)
