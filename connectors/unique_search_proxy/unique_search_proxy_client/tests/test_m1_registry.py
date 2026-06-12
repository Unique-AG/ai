from typing import Any

import pytest
from pydantic import BaseModel
from unique_search_proxy_core.crawlers import parse_crawler_config
from unique_search_proxy_core.crawlers.base import CrawlerType
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlRequest
from unique_search_proxy_core.crawlers.config_types import (
    crawler_config_from_request,
    parse_crawl_request,
)
from unique_search_proxy_core.crawlers.tavily.schema import TavilyCrawlRequest
from unique_search_proxy_core.errors import EngineNotConfiguredError
from unique_search_proxy_core.search_engines import (
    SearchEngineType,
    parse_search_engine_config,
)
from unique_search_proxy_core.search_engines.base import SearchEngine
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig

from unique_search_proxy_client.web.core.registry import (
    clear_registries_for_tests,
    get_search_engine,
    register_search_engine,
    registered_crawlers,
    registered_search_engines,
)


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    clear_registries_for_tests()
    yield
    clear_registries_for_tests()


class TestRegistry:
    @pytest.mark.ai
    def test_registries_start_empty(self) -> None:
        assert registered_search_engines() == frozenset()
        assert registered_crawlers() == frozenset()

    @pytest.mark.ai
    def test_get_search_engine_raises_when_unregistered(self) -> None:
        with pytest.raises(EngineNotConfiguredError):
            get_search_engine("google")

    @pytest.mark.ai
    def test_register_and_resolve_search_engine(self) -> None:
        class StubEngine(SearchEngine[Any]):
            engine_id = "stub"

            @property
            def mode(self) -> str:
                return "stub"

            async def search(self, call: BaseModel) -> tuple[list, list]:
                return [], []

        register_search_engine("stub", StubEngine)
        assert get_search_engine("stub") is StubEngine
        assert "stub" in registered_search_engines()


class TestDiscriminatedConfig:
    @pytest.mark.ai
    def test_search_engine_config_parses_google_discriminator(self) -> None:
        config = parse_search_engine_config(
            {"engine": "google", "dateRestrict": "d7"},
        )
        assert isinstance(config, GoogleConfig)
        assert config.engine == SearchEngineType.GOOGLE
        assert config.date_restrict is not None
        assert config.date_restrict.value == "d7"

    @pytest.mark.ai
    def test_crawler_config_parses_crawler_field(self) -> None:
        config = parse_crawler_config({"crawler": CrawlerType.BASIC.value})
        assert isinstance(config, BasicCrawlRequest)
        assert config.crawler == CrawlerType.BASIC

    @pytest.mark.ai
    def test_crawler_config_from_request_uses_crawler_discriminator(self) -> None:
        request = parse_crawl_request(
            {
                "urls": ["https://example.com"],
                "crawler": CrawlerType.TAVILY.value,
                "extractDepth": "basic",
                "timeout": 20,
            },
        )
        config = crawler_config_from_request(request)
        assert isinstance(config, TavilyCrawlRequest)
        assert config.extract_depth == "basic"
