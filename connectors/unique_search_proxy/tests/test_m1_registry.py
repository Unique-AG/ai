import pytest

from unique_search_proxy.web.core.crawlers import parse_crawler_config
from unique_search_proxy.web.core.crawlers.basic.schema import BasicCrawlerConfig
from unique_search_proxy.web.core.errors import EngineNotConfiguredError
from unique_search_proxy.web.core.registry import (
    clear_registries_for_tests,
    get_search_engine,
    register_search_engine,
    registered_crawlers,
    registered_search_engines,
)
from unique_search_proxy.web.core.search_engines import (
    SearchEngineType,
    parse_search_engine_config,
)
from unique_search_proxy.web.core.search_engines.base import SearchEngine
from unique_search_proxy.web.core.search_engines.google.schema import GoogleConfig


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
        class StubEngine(SearchEngine):
            engine_id = "stub"

            @property
            def snippet_only(self) -> bool:
                return True

            @property
            def mode(self) -> str:
                return "stub"

            async def search(self, call, *, timeout):
                return [], []

        register_search_engine("stub", StubEngine)
        assert get_search_engine("stub") is StubEngine
        assert "stub" in registered_search_engines()


class TestDiscriminatedConfig:
    @pytest.mark.ai
    def test_search_engine_config_parses_google_discriminator(self) -> None:
        config = parse_search_engine_config(
            {"engine": "google", "exposedFields": ["dateRestrict"]},
        )
        assert isinstance(config, GoogleConfig)
        assert config.engine == SearchEngineType.GOOGLE
        assert config.exposed_fields == ["dateRestrict"]

    @pytest.mark.ai
    def test_crawler_config_parses_crawler_field(self) -> None:
        config = parse_crawler_config({"crawler": "basic"})
        assert isinstance(config, BasicCrawlerConfig)
        assert config.crawler == "basic"
