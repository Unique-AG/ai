from typing import Any
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

    @pytest.mark.ai
    def test_get_search_engine_service__returns_google_search__with_google_config(
        self,
    ) -> None:
        """
        Purpose: Verify factory returns GoogleSearch instance for GoogleConfig.
        Why this matters: Ensures correct search engine service instantiation for Google.
        Setup summary: Create GoogleConfig, call factory with mocked dependencies, assert GoogleSearch instance.
        """
        # Arrange
        config: GoogleConfig = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)

        # Act
        service: Any = get_search_engine_service(config, Mock(), Mock())

        # Assert
        assert isinstance(service, GoogleSearch)

    @pytest.mark.ai
    def test_get_search_engine_service__returns_jina_search__with_jina_config(
        self,
    ) -> None:
        """
        Purpose: Verify factory returns JinaSearch instance for JinaConfig.
        Why this matters: Ensures correct search engine service instantiation for Jina.
        Setup summary: Create JinaConfig, call factory with mocked dependencies, assert JinaSearch instance.
        """
        # Arrange
        config: JinaConfig = JinaConfig(search_engine_name=SearchEngineType.JINA)

        # Act
        service: Any = get_search_engine_service(config, Mock(), Mock())

        # Assert
        assert isinstance(service, JinaSearch)

    @pytest.mark.ai
    def test_get_search_engine_service__returns_tavily_search__with_tavily_config(
        self,
    ) -> None:
        """
        Purpose: Verify factory returns TavilySearch instance for TavilyConfig.
        Why this matters: Ensures correct search engine service instantiation for Tavily.
        Setup summary: Create TavilyConfig, call factory with mocked dependencies, assert TavilySearch instance.
        """
        # Arrange
        config: TavilyConfig = TavilyConfig(search_engine_name=SearchEngineType.TAVILY)

        # Act
        service: Any = get_search_engine_service(config, Mock(), Mock())

        # Assert
        assert isinstance(service, TavilySearch)

    @pytest.mark.ai
    def test_get_search_engine_config_types_from_names__returns_google_config__with_single_engine_name(
        self,
    ) -> None:
        """
        Purpose: Verify config type resolution returns GoogleConfig for single "google" name.
        Why this matters: Ensures proper config type mapping from engine names.
        Setup summary: Pass ["google"] to resolver, assert GoogleConfig returned.
        """
        # Arrange
        engine_names: list[str] = ["google"]

        # Act
        config_type: Any = get_search_engine_config_types_from_names(engine_names)

        # Assert
        assert config_type == GoogleConfig

    @pytest.mark.ai
    def test_get_default_search_engine_config__returns_google_config__with_multiple_engine_names(
        self,
    ) -> None:
        """
        Purpose: Verify default config selection returns GoogleConfig when multiple engines specified.
        Why this matters: Ensures Google is prioritized as default search engine.
        Setup summary: Pass ["google", "jina"] to selector, assert GoogleConfig returned.
        """
        # Arrange
        engine_names: list[str] = ["google", "jina"]

        # Act
        config: Any = get_default_search_engine_config(engine_names)

        # Assert
        assert config == GoogleConfig


class TestSearchEngineConfigs:
    """Test search engine configuration models."""

    @pytest.mark.ai
    def test_google_config__creates_with_defaults__when_only_engine_name_provided(
        self,
    ) -> None:
        """
        Purpose: Verify GoogleConfig creates with default fetch_size and required attributes.
        Why this matters: Ensures proper default configuration for Google search engine.
        Setup summary: Create GoogleConfig with only engine_name, assert defaults and attributes present.
        """
        # Arrange
        engine_name: SearchEngineType = SearchEngineType.GOOGLE

        # Act
        config: GoogleConfig = GoogleConfig(search_engine_name=engine_name)

        # Assert
        assert config.search_engine_name == SearchEngineType.GOOGLE
        assert hasattr(config, "fetch_size")
        assert hasattr(config, "custom_search_config")
        assert config.fetch_size == 5  # default value

    @pytest.mark.ai
    def test_google_config__sets_custom_fetch_size__when_provided(self) -> None:
        """
        Purpose: Verify GoogleConfig accepts and stores custom fetch_size value.
        Why this matters: Ensures flexibility in configuring result fetch size.
        Setup summary: Create GoogleConfig with custom fetch_size=10, assert value stored correctly.
        """
        # Arrange
        engine_name: SearchEngineType = SearchEngineType.GOOGLE
        custom_fetch_size: int = 10

        # Act
        config: GoogleConfig = GoogleConfig(
            search_engine_name=engine_name,
            fetch_size=custom_fetch_size,
        )

        # Assert
        assert config.fetch_size == 10

    @pytest.mark.ai
    def test_jina_config__creates_with_required_attributes__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify JinaConfig creates with required attributes present.
        Why this matters: Ensures proper configuration structure for Jina search engine.
        Setup summary: Create JinaConfig, assert engine_name and required attributes exist.
        """
        # Arrange
        engine_name: SearchEngineType = SearchEngineType.JINA

        # Act
        config: JinaConfig = JinaConfig(search_engine_name=engine_name)

        # Assert
        assert config.search_engine_name == SearchEngineType.JINA
        assert hasattr(config, "fetch_size")
        assert hasattr(config, "custom_search_config")

    @pytest.mark.ai
    def test_tavily_config__creates_with_required_attributes__when_initialized(
        self,
    ) -> None:
        """
        Purpose: Verify TavilyConfig creates with required attributes present.
        Why this matters: Ensures proper configuration structure for Tavily search engine.
        Setup summary: Create TavilyConfig, assert engine_name and required attributes exist.
        """
        # Arrange
        engine_name: SearchEngineType = SearchEngineType.TAVILY

        # Act
        config: TavilyConfig = TavilyConfig(search_engine_name=engine_name)

        # Assert
        assert config.search_engine_name == SearchEngineType.TAVILY
        assert hasattr(config, "fetch_size")
        assert hasattr(config, "custom_search_config")


class TestSearchEngineTypes:
    """Test search engine type definitions."""

    @pytest.mark.ai
    def test_search_engine_type__has_expected_values__for_all_engine_types(
        self,
    ) -> None:
        """
        Purpose: Verify SearchEngineType enum contains all expected engine type values.
        Why this matters: Ensures all supported search engines are properly defined.
        Setup summary: Assert each SearchEngineType constant equals expected string value.
        """
        # Arrange & Act & Assert
        assert SearchEngineType.GOOGLE == "Google"
        assert SearchEngineType.JINA == "Jina"
        assert SearchEngineType.FIRECRAWL == "Firecrawl"
        assert SearchEngineType.TAVILY == "Tavily"
        assert SearchEngineType.BRAVE == "Brave"
        assert SearchEngineType.BING == "Bing"
        assert SearchEngineType.DUCKDUCKGO == "DuckDuckGo"

    @pytest.mark.ai
    def test_search_engine_type__validates_membership__for_valid_and_invalid_names(
        self,
    ) -> None:
        """
        Purpose: Verify SearchEngineType membership operator correctly identifies valid and invalid names.
        Why this matters: Ensures type safety when checking engine type validity.
        Setup summary: Assert valid names are in SearchEngineType, invalid name is not.
        """
        # Arrange & Act & Assert
        assert "Google" in SearchEngineType
        assert "Jina" in SearchEngineType
        assert "Tavily" in SearchEngineType
        assert "invalid_engine" not in SearchEngineType


class TestSearchEngineInstances:
    """Test search engine instance creation."""

    @pytest.mark.ai
    def test_google_search__initializes_correctly__with_google_config(self) -> None:
        """
        Purpose: Verify GoogleSearch initializes with config and required methods.
        Why this matters: Ensures GoogleSearch instance has correct structure and interface.
        Setup summary: Create GoogleConfig, instantiate GoogleSearch, assert config and methods present.
        """
        # Arrange
        config: GoogleConfig = GoogleConfig(search_engine_name=SearchEngineType.GOOGLE)

        # Act
        search: GoogleSearch = GoogleSearch(config)

        # Assert
        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")

    @pytest.mark.ai
    def test_jina_search__initializes_correctly__with_jina_config(self) -> None:
        """
        Purpose: Verify JinaSearch initializes with config and required methods.
        Why this matters: Ensures JinaSearch instance has correct structure and interface.
        Setup summary: Create JinaConfig, instantiate JinaSearch, assert config and methods present.
        """
        # Arrange
        config: JinaConfig = JinaConfig(search_engine_name=SearchEngineType.JINA)

        # Act
        search: JinaSearch = JinaSearch(config)

        # Assert
        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")

    @pytest.mark.ai
    def test_tavily_search__initializes_correctly__with_tavily_config(self) -> None:
        """
        Purpose: Verify TavilySearch initializes with config and required methods.
        Why this matters: Ensures TavilySearch instance has correct structure and interface.
        Setup summary: Create TavilyConfig, instantiate TavilySearch, assert config and methods present.
        """
        # Arrange
        config: TavilyConfig = TavilyConfig(search_engine_name=SearchEngineType.TAVILY)

        # Act
        search: TavilySearch = TavilySearch(config)

        # Assert
        assert search.config == config
        assert hasattr(search, "requires_scraping")
        assert hasattr(search, "search")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
