import pytest
from pydantic import BaseModel, ValidationError

from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import (
    BasicConfig,
    BasicCrawlRequest,
)
from unique_search_proxy_core.crawlers.config_types import (
    parse_crawl_request,
    parse_crawler_config,
)
from unique_search_proxy_core.crawlers.params import merge_crawler_config_and_invocation
from unique_search_proxy_core.providers.schema import provider_default_config


class TestCrawlerConfigRequestSplit:
    @pytest.mark.ai
    def test_config_parses_without_urls(self) -> None:
        config = parse_crawler_config({"crawler": CrawlerType.BASIC.value})
        assert isinstance(config, BasicConfig)

    @pytest.mark.ai
    def test_config_rejects_urls(self) -> None:
        with pytest.raises(ValidationError):
            parse_crawler_config(
                {
                    "crawler": CrawlerType.BASIC.value,
                    "urls": ["https://example.com"],
                },
            )

    @pytest.mark.ai
    def test_default_config_json_has_no_urls(self) -> None:
        defaults = provider_default_config("crawler", CrawlerType.BASIC.value)
        assert "urls" not in defaults

    @pytest.mark.ai
    def test_crawl_request_requires_urls(self) -> None:
        with pytest.raises(ValidationError):
            parse_crawl_request({"crawler": CrawlerType.BASIC.value})

    @pytest.mark.ai
    def test_merge_produces_crawl_request(self) -> None:
        config = BasicConfig()
        request = merge_crawler_config_and_invocation(
            config,
            {"urls": ["https://example.com"]},
        )
        assert isinstance(request, BaseModel)
        assert request.urls == ["https://example.com"]
        assert type(request) is BasicCrawlRequest
