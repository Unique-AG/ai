import pytest
from pydantic import ValidationError

from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicConfig
from unique_search_proxy_core.crawlers.config_types import (
    parse_crawl_request,
    parse_crawler_config,
)
from unique_search_proxy_core.providers.schema import provider_default_config


class TestCrawlerConfigRequestSplit:
    @pytest.mark.ai
    def test_config_parses_without_urls(self) -> None:
        config = parse_crawler_config({"crawler": CrawlerType.BASIC.value})
        assert isinstance(config, BasicConfig)

    @pytest.mark.ai
    def test_config_ignores_urls(self) -> None:
        # Crawler deployment configs mirror the search-engine configs: they do
        # not set ``extra='forbid'`` (that would emit ``additionalProperties:
        # false`` and break the RJSF admin form's discriminated ``oneOf``). The
        # config/request split is preserved because ``urls`` is not a config
        # field: it is silently dropped, never surfaced on the parsed model.
        config = parse_crawler_config(
            {
                "crawler": CrawlerType.BASIC.value,
                "urls": ["https://example.com"],
            },
        )
        assert isinstance(config, BasicConfig)
        assert not hasattr(config, "urls")
        assert "urls" not in config.model_dump()
        assert "urls" not in BasicConfig.model_json_schema().get("properties", {})

    @pytest.mark.ai
    def test_default_config_json_has_no_urls(self) -> None:
        defaults = provider_default_config("crawler", CrawlerType.BASIC.value)
        assert "urls" not in defaults

    @pytest.mark.ai
    def test_crawl_request_requires_urls(self) -> None:
        with pytest.raises(ValidationError):
            parse_crawl_request({"crawler": CrawlerType.BASIC.value})
