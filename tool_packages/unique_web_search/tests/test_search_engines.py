from unittest.mock import Mock

import pytest

from unique_web_search.services.search_engine import (
    get_default_search_engine_config,
    get_search_engine_config_types_from_names,
    get_search_engine_service,
)
from unique_web_search.services.search_engine.base import SearchEngineType
from unique_web_search.services.search_engine.google import GoogleConfig, GoogleSearch
from unique_web_search.services.search_engine.jina import JinaConfig, JinaSearch
from unique_web_search.services.search_engine.tavily import TavilyConfig, TavilySearch


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

    def test_search_engine_type_membership(self):
        """Test SearchEngineType membership."""
        assert "Google" in SearchEngineType
        assert "Jina" in SearchEngineType
        assert "Tavily" in SearchEngineType
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
