"""Tests for the crawler self-registration registry."""

from __future__ import annotations

from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig
from unique_search_proxy_core.crawlers.firecrawl.schema import FirecrawlConfig
from unique_search_proxy_core.crawlers.jina.schema import JinaConfig
from unique_search_proxy_core.crawlers.tavily.schema import TavilyConfig

from unique_web_search.services.crawlers.registry import CRAWLER_REGISTRY

_EXPECTED_CONFIG_BASES: dict[CrawlerType, type] = {
    CrawlerType.BASIC: BasicConfig,
    CrawlerType.TAVILY: TavilyConfig,
    CrawlerType.JINA: JinaConfig,
    CrawlerType.FIRECRAWL: FirecrawlConfig,
}


def test_crawler_registry__autodiscover__registers_all_crawlers() -> None:
    assert len(CRAWLER_REGISTRY.specs) == 4


def test_crawler_registry__enum_coverage__includes_all_discriminators() -> None:
    CRAWLER_REGISTRY.assert_enum_coverage(CrawlerType)


def test_crawler_registry__config_classes__extend_static_bases() -> None:
    for spec in CRAWLER_REGISTRY.specs:
        base_cls = _EXPECTED_CONFIG_BASES[spec.key]
        assert issubclass(spec.config_cls, base_cls)
        assert (
            spec.config_cls.model_json_schema().get("title") == spec.config_display_name
        )


def test_crawler_registry__name_to_config__has_expected_keys() -> None:
    assert set(CRAWLER_REGISTRY.name_to_config()) == {
        "basic",
        "tavily",
        "jina",
        "firecrawl",
    }
