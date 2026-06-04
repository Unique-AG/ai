import pytest
from unique_search_proxy_core.crawlers import parse_crawler_config
from unique_search_proxy_core.crawlers.basic.schema import BasicCrawlerConfig
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
            {"engine": "google", "dateRestrict": "d7"},
        )
        assert isinstance(config, GoogleConfig)
        assert config.engine == SearchEngineType.GOOGLE
        assert config.date_restrict is not None
        assert config.date_restrict.value == "d7"

    @pytest.mark.ai
    def test_crawler_config_parses_crawler_field(self) -> None:
        config = parse_crawler_config({"crawler": "basic"})
        assert isinstance(config, BasicCrawlerConfig)
        assert config.crawler == "basic"
