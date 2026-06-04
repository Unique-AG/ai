from __future__ import annotations

from typing import TypeAlias

from pydantic import TypeAdapter

from unique_search_proxy_core.crawlers.base import BaseCrawlerConfig, CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerConfig

CrawlerConfigTypes: TypeAlias = BasicCrawlerConfig

CRAWLER_NAME_TO_CONFIG: dict[str, type[BaseCrawlerConfig]] = {
    CrawlerType.BASIC.value: BasicCrawlerConfig,
}

_crawler_config_adapter: TypeAdapter[CrawlerConfigTypes] = TypeAdapter(
    CrawlerConfigTypes,
)


def parse_crawler_config(data: object) -> CrawlerConfigTypes:
    return _crawler_config_adapter.validate_python(data)
