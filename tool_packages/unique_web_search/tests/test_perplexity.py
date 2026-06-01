from unittest.mock import AsyncMock, Mock, patch

import pytest
from perplexity import Omit
from perplexity.types.search_create_response import Result as PerplexitySearchResult

from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.perplexity import (
    MAX_RESULTS_PER_REQUEST,
    PerplexitySearch,
    PerplexitySearchConfig,
)
from unique_web_search.services.search_engine.schema import WebSearchResult

_OPTIONAL_SEARCH_PARAMS = (
    "country",
    "max_tokens",
    "search_mode",
    "search_recency_filter",
    "search_type",
)


def _assert_search_create_call(
    mock_create: AsyncMock,
    *,
    query: str,
    max_results: int,
    config: PerplexitySearchConfig | None = None,
) -> None:
    mock_create.assert_awaited_once()
    kwargs = mock_create.await_args.kwargs
    assert kwargs["query"] == query
    assert kwargs["max_results"] == max_results

    config = config or PerplexitySearchConfig()
    for param in _OPTIONAL_SEARCH_PARAMS:
        expected = getattr(config, param)
        actual = kwargs[param]
        if expected is None:
            assert isinstance(actual, Omit), f"{param} should be Omit when unset"
        else:
            assert actual == expected


class TestPerplexitySearchConfig:
    def test_default_requires_scraping_is_false(self):
        config = PerplexitySearchConfig(search_engine_name=SearchEngineType.PERPLEXITY)
        assert config.requires_scraping is False

    def test_default_search_engine_name(self):
        config = PerplexitySearchConfig()
        assert config.search_engine_name == SearchEngineType.PERPLEXITY

    def test_default_fetch_size(self):
        config = PerplexitySearchConfig()
        assert config.fetch_size == 5

    def test_model_config_title(self):
        config = PerplexitySearchConfig()
        assert config.model_config.get("title") == "Perplexity Search"


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
        search = PerplexitySearch(PerplexitySearchConfig())
        assert search.is_configured is True

    def test_requires_scraping_delegates_to_config(self, _mock_perplexity_settings):
        config_no = PerplexitySearchConfig(requires_scraping=False)
        config_yes = PerplexitySearchConfig(requires_scraping=True)

        assert PerplexitySearch(config_no).requires_scraping is False
        assert PerplexitySearch(config_yes).requires_scraping is True


class TestPerplexitySearchToWebSearchResults:
    def test_maps_results(self, _mock_perplexity_settings):
        search = PerplexitySearch(PerplexitySearchConfig())
        results = search._to_web_search_results(
            [
                PerplexitySearchResult(
                    title="Example",
                    url="https://example.com",
                    snippet="A snippet",
                )
            ]
        )
        assert results == [
            WebSearchResult(
                url="https://example.com",
                title="Example",
                snippet="A snippet",
            )
        ]

    def test_empty_snippet_fallback(self, _mock_perplexity_settings):
        search = PerplexitySearch(PerplexitySearchConfig())
        results = search._to_web_search_results(
            [
                PerplexitySearchResult(
                    title="Example",
                    url="https://example.com",
                    snippet="",
                )
            ]
        )
        assert results[0].snippet == "No Snippet Found"

    def test_empty_results(self, _mock_perplexity_settings):
        search = PerplexitySearch(PerplexitySearchConfig())
        assert search._to_web_search_results(None) == []
        assert search._to_web_search_results([]) == []


class TestPerplexitySearch:
    @pytest.mark.asyncio
    async def test_search_calls_api_with_clamped_max_results(
        self, _mock_perplexity_settings
    ):
        config = PerplexitySearchConfig(fetch_size=50)
        search = PerplexitySearch(config)

        mock_result = PerplexitySearchResult(
            title="Hit",
            url="https://example.com/page",
            snippet="Details",
        )
        mock_response = Mock(results=[mock_result])
        mock_create = AsyncMock(return_value=mock_response)
        mock_search_resource = Mock(create=mock_create)
        mock_client = Mock()
        mock_client.search = mock_search_resource
        mock_client.close = AsyncMock()

        with patch(
            "unique_web_search.services.search_engine.perplexity.AsyncPerplexity",
            return_value=mock_client,
        ) as mock_client_cls:
            results = await search.search("test query")

        mock_client_cls.assert_called_once()
        client_kwargs = mock_client_cls.call_args.kwargs
        assert client_kwargs["api_key"] == "test-key"
        assert client_kwargs["http_client"] is not None
        _assert_search_create_call(
            mock_create,
            query="test query",
            max_results=MAX_RESULTS_PER_REQUEST,
            config=config,
        )
        mock_client.close.assert_awaited_once()
        assert results == [
            WebSearchResult(
                url="https://example.com/page",
                title="Hit",
                snippet="Details",
            )
        ]

    @pytest.mark.asyncio
    async def test_search_uses_fetch_size_when_below_api_max(
        self, _mock_perplexity_settings
    ):
        config = PerplexitySearchConfig(fetch_size=3)
        search = PerplexitySearch(config)

        mock_create = AsyncMock(return_value=Mock(results=[]))
        mock_client = Mock()
        mock_client.search = Mock(create=mock_create)
        mock_client.close = AsyncMock()

        with patch(
            "unique_web_search.services.search_engine.perplexity.AsyncPerplexity",
            return_value=mock_client,
        ):
            await search.search("q")

        _assert_search_create_call(
            mock_create,
            query="q",
            max_results=3,
            config=config,
        )

    @pytest.mark.asyncio
    async def test_search_passes_optional_config_to_api(
        self, _mock_perplexity_settings
    ):
        config = PerplexitySearchConfig(
            fetch_size=3,
            country="US",
            max_tokens=1024,
            search_mode="academic",
            search_recency_filter="week",
            search_type="people",
        )
        search = PerplexitySearch(config)

        mock_create = AsyncMock(return_value=Mock(results=[]))
        mock_client = Mock()
        mock_client.search = Mock(create=mock_create)
        mock_client.close = AsyncMock()

        with patch(
            "unique_web_search.services.search_engine.perplexity.AsyncPerplexity",
            return_value=mock_client,
        ):
            await search.search("q")

        _assert_search_create_call(
            mock_create,
            query="q",
            max_results=3,
            config=config,
        )
