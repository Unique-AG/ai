from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.search_engine import (
    get_default_search_engine_config,
    get_search_engine_config_types_from_names,
    get_search_engine_service,
)
from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.google import GoogleConfig, GoogleSearch
from unique_web_search.services.search_engine.jina import JinaConfig, JinaSearch
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
    WebSearchResults,
)
from unique_web_search.services.search_engine.tavily import TavilyConfig, TavilySearch
from unique_web_search.services.search_engine.vertexai import (
    VertexAI,
    VertexAIConfig,
    resolve_all,
    resolve_url,
)


class TestSearchEngineFactory:
    """Test search engine factory functions."""

    def test_get_google_search_engine_service(self):
        """Test getting Google search engine service."""
        config = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)
        service = get_search_engine_service(config, Mock(), Mock())
        assert isinstance(service, GoogleSearch)

    def test_get_jina_search_engine_service(self):
        """Test getting Jina search engine service."""
        config = JinaConfig(search_engine_name=SearchEngineType.JINA)
        service = get_search_engine_service(config, Mock(), Mock())
        assert isinstance(service, JinaSearch)

    def test_get_tavily_search_engine_service(self):
        """Test getting Tavily search engine service."""
        config = TavilyConfig(search_engine_name=SearchEngineType.TAVILY)
        service = get_search_engine_service(config, Mock(), Mock())
        assert isinstance(service, TavilySearch)

    def test_get_vertexai_search_engine_service(self):
        """Test getting VertexAI search engine service."""
        config = VertexAIConfig(search_engine_name=SearchEngineType.VERTEXAI)
        service = get_search_engine_service(config, Mock(), Mock())
        assert isinstance(service, VertexAI)

    def test_get_config_types_from_names_single(self):
        """Test getting config types from single engine name."""
        config_type = get_search_engine_config_types_from_names(["google"])
        assert config_type == GoogleConfig

    def test_get_default_search_engine_config(self):
        """Test getting default search engine config."""
        config = get_default_search_engine_config(["google", "jina"])
        assert config == GoogleConfig


class TestSearchEngineConfigs:
    """Test search engine configuration models."""

    def test_google_config_creation(self):
        """Test GoogleConfig creation."""
        config = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)

        assert config.search_engine_name == SearchEngineType.GOOGLE
        assert hasattr(config, "fetch_size")
        assert hasattr(config, "custom_search_config")
        assert config.fetch_size == 5  # default value

    def test_google_config_custom_fetch_size(self):
        """Test GoogleConfig with custom fetch size."""
        config = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE, fetch_size=10)
        assert config.fetch_size == 10

    def test_jina_config_creation(self):
        """Test JinaConfig creation."""
        config = JinaConfig(search_engine_name=SearchEngineType.JINA)

        assert config.search_engine_name == SearchEngineType.JINA
        assert hasattr(config, "fetch_size")
        assert hasattr(config, "custom_search_config")

    def test_tavily_config_creation(self):
        """Test TavilyConfig creation."""
        config = TavilyConfig(search_engine_name=SearchEngineType.TAVILY)

        assert config.search_engine_name == SearchEngineType.TAVILY
        assert hasattr(config, "fetch_size")
        assert hasattr(config, "custom_search_config")

    def test_vertexai_config_creation(self):
        """Test VertexAIConfig creation."""
        config = VertexAIConfig(search_engine_name=SearchEngineType.VERTEXAI)

        assert config.search_engine_name == SearchEngineType.VERTEXAI
        assert hasattr(config, "model_name")
        assert hasattr(config, "grounding_system_instruction")
        assert hasattr(config, "requires_scraping")
        assert hasattr(config, "enable_entreprise_search")
        assert hasattr(config, "enable_redirect_resolution")
        assert config.model_name == "gemini-2.5-flash"  # default value
        assert not config.requires_scraping  # default value
        assert not config.enable_entreprise_search  # default value
        assert config.enable_redirect_resolution  # default value

    def test_vertexai_config_custom_values(self):
        """Test VertexAIConfig with custom values."""
        config = VertexAIConfig(
            search_engine_name=SearchEngineType.VERTEXAI,
            model_name="gemini-2.5-pro",
            grounding_system_instruction="Custom instruction",
            requires_scraping=True,
            enable_entreprise_search=True,
            enable_redirect_resolution=False,
        )

        assert config.model_name == "gemini-2.5-pro"
        assert config.grounding_system_instruction == "Custom instruction"
        assert config.requires_scraping
        assert config.enable_entreprise_search
        assert not config.enable_redirect_resolution


class TestSearchEngineTypes:
    """Test search engine type definitions."""

    def test_search_engine_type_values(self):
        """Test that SearchEngineType enum has expected values."""
        assert SearchEngineType.GOOGLE == "Google"
        assert SearchEngineType.JINA == "Jina"
        assert SearchEngineType.FIRECRAWL == "Firecrawl"
        assert SearchEngineType.TAVILY == "Tavily"
        assert SearchEngineType.BRAVE == "Brave"
        assert SearchEngineType.BING == "Bing"
        assert SearchEngineType.DUCKDUCKGO == "DuckDuckGo"
        assert SearchEngineType.VERTEXAI == "VertexAI"

    def test_search_engine_type_membership(self):
        """Test SearchEngineType membership."""
        assert "Google" in SearchEngineType
        assert "Jina" in SearchEngineType
        assert "Tavily" in SearchEngineType
        assert "VertexAI" in SearchEngineType
        assert "invalid_engine" not in SearchEngineType


class TestSearchEngineInstances:
    """Test search engine instance creation."""

    def test_google_search_initialization(self):
        """Test GoogleSearch initializes correctly."""
        config = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)
        search = GoogleSearch(config)

        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")

    def test_jina_search_initialization(self):
        """Test JinaSearch initializes correctly."""
        config = JinaConfig(search_engine_name=SearchEngineType.JINA)
        search = JinaSearch(config)

        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")

    def test_tavily_search_initialization(self):
        """Test TavilySearch initializes correctly."""
        config = TavilyConfig(search_engine_name=SearchEngineType.TAVILY)
        search = TavilySearch(config)

        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")

    def test_vertexai_search_initialization(self):
        """Test VertexAI initializes correctly."""
        config = VertexAIConfig(search_engine_name=SearchEngineType.VERTEXAI)
        search = VertexAI(config, Mock(), Mock())

        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")
        assert hasattr(search, "client")
        assert hasattr(search, "is_configured")


class TestVertexAISearch:
    """Test VertexAI search engine specific functionality."""

    @pytest.mark.asyncio
    async def test_vertexai_search_with_redirect_resolution(self, mocker):
        """Test VertexAI search with redirect resolution enabled."""
        config = VertexAIConfig(
            search_engine_name=SearchEngineType.VERTEXAI,
            enable_redirect_resolution=True,
        )

        # Mock the Vertex AI client and functions
        mock_client = AsyncMock()
        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.get_vertex_client",
            return_value=mock_client,
        )

        # Mock generate_content
        mock_generate = AsyncMock()
        mock_generate.side_effect = [
            "Answer with citations",  # First call returns answer
            WebSearchResults(
                results=[
                    WebSearchResult(
                        url="http://example.com",
                        title="Test",
                        snippet="Test snippet",
                        content="Test content",
                    )
                ]
            ),  # Second call returns structured results
        ]
        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.generate_content",
            mock_generate,
        )

        # Mock resolve_all
        mock_resolve = AsyncMock()
        mock_resolve.return_value = WebSearchResults(
            results=[
                WebSearchResult(
                    url="https://example.com",  # Resolved URL
                    title="Test",
                    snippet="Test snippet",
                    content="Test content",
                )
            ]
        )
        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.resolve_all",
            mock_resolve,
        )

        search = VertexAI(config, Mock(), Mock())
        results = await search.search("test query")

        assert len(results) == 1
        assert results[0].url == "https://example.com"
        mock_resolve.assert_called_once()

    @pytest.mark.asyncio
    async def test_vertexai_search_without_redirect_resolution(self, mocker):
        """Test VertexAI search with redirect resolution disabled."""
        config = VertexAIConfig(
            search_engine_name=SearchEngineType.VERTEXAI,
            enable_redirect_resolution=False,
        )

        # Mock the Vertex AI client and functions
        mock_client = AsyncMock()
        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.get_vertex_client",
            return_value=mock_client,
        )

        # Mock generate_content
        mock_generate = AsyncMock()
        mock_generate.side_effect = [
            "Answer with citations",
            WebSearchResults(
                results=[
                    WebSearchResult(
                        url="http://example.com",
                        title="Test",
                        snippet="Test snippet",
                        content="Test content",
                    )
                ]
            ),
        ]
        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.generate_content",
            mock_generate,
        )

        # Mock resolve_all - should not be called
        mock_resolve = AsyncMock()
        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.resolve_all",
            mock_resolve,
        )

        search = VertexAI(config, Mock(), Mock())
        results = await search.search("test query")

        assert len(results) == 1
        assert results[0].url == "http://example.com"
        mock_resolve.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_url_successful(self, mocker):
        """Test resolve_url successfully resolves a redirect."""
        from httpx import Response

        # Create a mock response with redirected URL
        mock_response = Mock(spec=Response)
        mock_response.url = "https://redirected-example.com"

        # Create a mock client
        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_response)

        web_search_result = WebSearchResult(
            url="http://example.com",
            title="Test",
            snippet="Test snippet",
            content="Test content",
        )

        result = await resolve_url(mock_client, web_search_result)

        assert result.url == "https://redirected-example.com"
        mock_client.head.assert_called_once_with(
            "http://example.com", follow_redirects=True
        )

    @pytest.mark.asyncio
    async def test_resolve_url_handles_exception(self, mocker):
        """Test resolve_url handles exceptions gracefully."""
        # Create a mock client that raises an exception
        mock_client = AsyncMock()
        mock_client.head = AsyncMock(side_effect=Exception("Network error"))

        web_search_result = WebSearchResult(
            url="http://example.com",
            title="Test",
            snippet="Test snippet",
            content="Test content",
        )

        result = await resolve_url(mock_client, web_search_result)

        # URL should remain unchanged
        assert result.url == "http://example.com"
        assert result == web_search_result

    @pytest.mark.asyncio
    async def test_resolve_all_resolves_multiple_urls(self, mocker):
        """Test resolve_all resolves multiple URLs in parallel."""

        # Mock resolve_url
        async def mock_resolve_url(client, result):
            result.url = result.url.replace("http://", "https://")
            return result

        mocker.patch(
            "unique_web_search.services.search_engine.vertexai.resolve_url",
            side_effect=mock_resolve_url,
        )

        web_search_results = WebSearchResults(
            results=[
                WebSearchResult(
                    url="http://example1.com",
                    title="Test 1",
                    snippet="Snippet 1",
                    content="Content 1",
                ),
                WebSearchResult(
                    url="http://example2.com",
                    title="Test 2",
                    snippet="Snippet 2",
                    content="Content 2",
                ),
            ]
        )

        result = await resolve_all(web_search_results)

        assert len(result.results) == 2
        assert result.results[0].url == "https://example1.com"
        assert result.results[1].url == "https://example2.com"

    def test_vertexai_requires_scraping_property(self):
        """Test VertexAI requires_scraping property."""
        config_no_scraping = VertexAIConfig(
            search_engine_name=SearchEngineType.VERTEXAI,
            requires_scraping=False,
        )
        config_with_scraping = VertexAIConfig(
            search_engine_name=SearchEngineType.VERTEXAI,
            requires_scraping=True,
        )

        search_no_scraping = VertexAI(config_no_scraping, Mock(), Mock())
        search_with_scraping = VertexAI(config_with_scraping, Mock(), Mock())

        assert not search_no_scraping.requires_scraping
        assert search_with_scraping.requires_scraping


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
