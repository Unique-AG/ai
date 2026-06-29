from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.search_engines import SearchEngineType
from unique_search_proxy_core.search_engines.brave.schema import BraveConfig

from unique_web_search.services.search_engine.brave import BraveSearch
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestBraveSearchConfig:
    def test_default_engine(self):
        config = BraveConfig()
        assert config.engine == SearchEngineType.BRAVE

    def test_default_fetch_size(self):
        config = BraveConfig()
        assert config.fetch_size == 10

    def test_custom_fetch_size(self):
        config = BraveConfig(fetch_size=30)
        assert config.fetch_size == 30

    def test_default_extra_snippets(self):
        config = BraveConfig()
        assert config.extra_snippets is True

    def test_default_safesearch_value(self):
        config = BraveConfig()
        assert config.safesearch.value == "moderate"
        assert config.safesearch.expose is False

    def test_default_country_is_inactive(self):
        config = BraveConfig()
        assert config.country.value is None
        assert config.country.expose is False


@pytest.fixture
def _mock_brave_settings():
    settings = Mock()
    settings.is_configured = True
    settings.api_key = "test-key"
    settings.api_endpoint = "https://api.search.brave.com/res/v1/web/search"
    with patch(
        "unique_web_search.services.search_engine.brave.get_brave_search_settings",
        return_value=settings,
    ):
        yield settings


class TestBraveSearchInit:
    def test_is_configured_from_settings(self, _mock_brave_settings):
        config = BraveConfig()
        search = BraveSearch(config)
        assert search.is_configured is True

    def test_requires_scraping_defaults_to_false(self, _mock_brave_settings):
        search = BraveSearch(BraveConfig())
        assert search.requires_scraping is False


class TestBraveSearch:
    @pytest.mark.asyncio
    async def test_legacy_search_raises_not_implemented(self, _mock_brave_settings):
        search = BraveSearch(BraveConfig())

        with pytest.raises(
            NotImplementedError,
            match="Brave search is not supported in the legacy mode",
        ):
            await search._legacy_search("query")

    @pytest.mark.asyncio
    async def test_proxy_search_passes_config_to_client(self, _mock_brave_settings):
        config = BraveConfig(fetch_size=3)
        search = BraveSearch(config)

        mock_response = Mock()
        mock_response.curated = [
            Mock(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
                content="",
            )
        ]
        mock_brave = AsyncMock(return_value=mock_response)

        with (
            patch(
                "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
                True,
            ),
            patch(
                "unique_web_search.services.search_engine.brave.open_search_proxy_client"
            ) as mock_open_client,
        ):
            mock_client = AsyncMock()
            mock_client.search.brave = mock_brave
            mock_open_client.return_value.__aenter__.return_value = mock_client

            results = await search.search("test query")

        mock_brave.assert_awaited_once_with(
            query="test query",
            fetch_size=3,
            extra_snippets=True,
            spellcheck=False,
            text_decorations=True,
            operators=True,
            ui_lang="en-US",
            units=None,
            summary=True,
            include_fetch_metadata=False,
            goggles=None,
            country=None,
            freshness=None,
            search_lang=None,
            safesearch="moderate",
            result_filter=None,
        )
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
            )
        ]
