from unittest.mock import AsyncMock, Mock, patch

import pytest
from unique_search_proxy_core.search_engines import SearchEngineType
from unique_search_proxy_core.search_engines.perplexity.schema import (
    ExposableDomainFilter,
    ExposableLanguageFilter,
    ExposableRecencyFilter,
    ExposableStrOrNone,
    PerplexityConfig,
)

from unique_web_search.services.search_engine.perplexity import PerplexitySearch
from unique_web_search.services.search_engine.schema import WebSearchResult


class TestPerplexitySearchConfig:
    def test_default_engine(self):
        config = PerplexityConfig()
        assert config.engine == SearchEngineType.PERPLEXITY

    def test_default_fetch_size(self):
        config = PerplexityConfig()
        assert config.fetch_size == 10

    def test_default_country_is_inactive(self):
        config = PerplexityConfig()
        assert config.country.value is None
        assert config.country.expose is False

    def test_default_max_tokens_is_none(self):
        config = PerplexityConfig()
        assert config.max_tokens is None


@pytest.fixture
def _mock_perplexity_settings():
    settings = Mock()
    settings.is_configured = True
    settings.api_key = "test-key"
    with patch(
        "unique_web_search.services.search_engine.perplexity.get_perplexity_search_settings",
        return_value=settings,
    ):
        yield settings


class TestPerplexitySearchInit:
    def test_is_configured_from_settings(self, _mock_perplexity_settings):
        search = PerplexitySearch(PerplexityConfig())
        assert search.is_configured is True


class TestPerplexitySearch:
    @pytest.mark.asyncio
    async def test_legacy_search_raises_not_implemented(
        self, _mock_perplexity_settings
    ):
        search = PerplexitySearch(PerplexityConfig())

        with pytest.raises(
            NotImplementedError,
            match="Perplexity search is not supported in the legacy mode",
        ):
            await search._legacy_search("query")

    @pytest.mark.asyncio
    async def test_proxy_search_passes_config_to_client(
        self, _mock_perplexity_settings
    ):
        config = PerplexityConfig(
            fetch_size=3,
            country="US",
            max_tokens=1024,
            max_tokens_per_page=512,
            search_recency_filter=ExposableRecencyFilter(expose=False, value="week"),
            search_domain_filter=ExposableDomainFilter(
                expose=False, value=["example.com"]
            ),
            search_language_filter=ExposableLanguageFilter(expose=False, value=["en"]),
            search_after_date_filter=ExposableStrOrNone(
                expose=False, value="01/01/2024"
            ),
        )
        search = PerplexitySearch(config)

        mock_response = Mock()
        mock_response.curated = [
            Mock(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
                content="",
            )
        ]
        mock_perplexity = AsyncMock(return_value=mock_response)

        with (
            patch(
                "unique_web_search.services.search_engine.base.search_proxy_client_enabled",
                True,
            ),
            patch(
                "unique_web_search.services.search_engine.perplexity.open_search_proxy_client"
            ) as mock_open_client,
        ):
            mock_client = AsyncMock()
            mock_client.search.perplexity = mock_perplexity
            mock_open_client.return_value.__aenter__.return_value = mock_client

            results = await search.search("test query")

        mock_perplexity.assert_awaited_once_with(
            query="test query",
            fetch_size=3,
            max_tokens=1024,
            max_tokens_per_page=512,
            country="US",
            search_context_size=None,
            search_language_filter=["en"],
            search_domain_filter=["example.com"],
            search_recency_filter="week",
            last_updated_after_filter=None,
            last_updated_before_filter=None,
            search_after_date_filter="01/01/2024",
            search_before_date_filter=None,
        )
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
            )
        ]
