"""Tests for client_settings module."""

import pytest

from unique_web_search.client_settings import (
    BraveSearchSettings,
    FirecrawlSearchSettings,
    GoogleSearchSettings,
    JinaSearchSettings,
    TavilySearchSettings,
    get_brave_search_settings,
    get_firecrawl_search_settings,
    get_google_search_settings,
    get_jina_search_settings,
    get_tavily_search_settings,
)


class TestGoogleSearchSettings:
    """Test GoogleSearchSettings class."""

    @pytest.mark.ai
    def test_google_search_settings__creates_with_all_fields__when_provided(
        self,
    ) -> None:
        """
        Purpose: Verify GoogleSearchSettings creates correctly with all configuration fields.
        Why this matters: Ensures proper structure for Google search API configuration.
        Setup summary: Create GoogleSearchSettings with api_key, search_engine_id, api_endpoint, assert all values stored.
        """
        # Arrange
        api_key: str = "test-api-key"
        search_engine_id: str = "test-engine-id"
        api_endpoint: str = "https://custom.googleapis.com"

        # Act
        settings: GoogleSearchSettings = GoogleSearchSettings(
            api_key=api_key,
            search_engine_id=search_engine_id,
            api_endpoint=api_endpoint,
        )

        # Assert
        assert settings.api_key == "test-api-key"
        assert settings.search_engine_id == "test-engine-id"
        assert settings.api_endpoint == "https://custom.googleapis.com"

    @pytest.mark.ai
    def test_google_search_settings__is_configured_returns_true__when_all_fields_set(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns True when all required fields are set.
        Why this matters: Enables validation of complete Google search API configuration.
        Setup summary: Create GoogleSearchSettings with all fields, assert is_configured is True.
        """
        # Arrange & Act
        settings: GoogleSearchSettings = GoogleSearchSettings(
            api_key="key",
            search_engine_id="id",
            api_endpoint="endpoint",
        )

        # Assert
        assert settings.is_configured is True

    @pytest.mark.ai
    def test_google_search_settings__is_configured_returns_false__when_any_field_missing(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns False when any required field is missing.
        Why this matters: Ensures incomplete configurations are properly detected.
        Setup summary: Create GoogleSearchSettings with missing fields, assert is_configured is False.
        """
        # Arrange & Act - Missing api_key
        settings1: GoogleSearchSettings = GoogleSearchSettings(
            api_key=None, search_engine_id="id", api_endpoint="endpoint"
        )
        # Assert
        assert settings1.is_configured is False

        # Arrange & Act - Missing search_engine_id
        settings2: GoogleSearchSettings = GoogleSearchSettings(
            api_key="key", search_engine_id=None, api_endpoint="endpoint"
        )
        # Assert
        assert settings2.is_configured is False

        # Arrange & Act - Missing api_endpoint
        settings3: GoogleSearchSettings = GoogleSearchSettings(
            api_key="key", search_engine_id="id", api_endpoint=None
        )
        # Assert
        assert settings3.is_configured is False

    @pytest.mark.ai
    def test_google_search_settings__from_env_settings__creates_from_environment(
        self, monkeypatch
    ) -> None:
        """
        Purpose: Verify from_env_settings creates settings from environment variables.
        Why this matters: Ensures proper integration with environment-based configuration.
        Setup summary: Set environment variables, call from_env_settings, assert values loaded correctly.
        """
        # Arrange
        from unique_web_search.settings import env_settings

        monkeypatch.setattr(env_settings, "google_search_api_key", "env-key")
        monkeypatch.setattr(env_settings, "google_search_engine_id", "env-id")
        monkeypatch.setattr(env_settings, "google_search_api_endpoint", "env-endpoint")

        # Act
        settings: GoogleSearchSettings = GoogleSearchSettings.from_env_settings()

        # Assert
        assert settings.api_key == "env-key"
        assert settings.search_engine_id == "env-id"
        assert settings.api_endpoint == "env-endpoint"

    @pytest.mark.ai
    def test_get_google_search_settings__returns_singleton__on_multiple_calls(
        self,
    ) -> None:
        """
        Purpose: Verify get_google_search_settings returns same instance on multiple calls.
        Why this matters: Ensures singleton pattern for settings instance.
        Setup summary: Call get_google_search_settings twice, assert same instance returned.
        """
        # Arrange & Act
        settings1 = get_google_search_settings()
        settings2 = get_google_search_settings()

        # Assert
        assert settings1 is settings2


class TestFirecrawlSearchSettings:
    """Test FirecrawlSearchSettings class."""

    @pytest.mark.ai
    def test_firecrawl_search_settings__creates_with_api_key__when_provided(
        self,
    ) -> None:
        """
        Purpose: Verify FirecrawlSearchSettings creates correctly with API key.
        Why this matters: Ensures proper structure for Firecrawl search API configuration.
        Setup summary: Create FirecrawlSearchSettings with api_key, assert value stored.
        """
        # Arrange
        api_key: str = "test-firecrawl-key"

        # Act
        settings: FirecrawlSearchSettings = FirecrawlSearchSettings(api_key=api_key)

        # Assert
        assert settings.api_key == "test-firecrawl-key"

    @pytest.mark.ai
    def test_firecrawl_search_settings__is_configured_returns_true__when_api_key_set(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns True when API key is set.
        Why this matters: Enables validation of complete Firecrawl search API configuration.
        Setup summary: Create FirecrawlSearchSettings with api_key, assert is_configured is True.
        """
        # Arrange & Act
        settings: FirecrawlSearchSettings = FirecrawlSearchSettings(api_key="key")

        # Assert
        assert settings.is_configured is True

    @pytest.mark.ai
    def test_firecrawl_search_settings__is_configured_returns_false__when_api_key_missing(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns False when API key is missing.
        Why this matters: Ensures incomplete configurations are properly detected.
        Setup summary: Create FirecrawlSearchSettings with None api_key, assert is_configured is False.
        """
        # Arrange & Act
        settings: FirecrawlSearchSettings = FirecrawlSearchSettings(api_key=None)

        # Assert
        assert settings.is_configured is False

    @pytest.mark.ai
    def test_get_firecrawl_search_settings__returns_singleton__on_multiple_calls(
        self,
    ) -> None:
        """
        Purpose: Verify get_firecrawl_search_settings returns same instance on multiple calls.
        Why this matters: Ensures singleton pattern for settings instance.
        Setup summary: Call get_firecrawl_search_settings twice, assert same instance returned.
        """
        # Arrange & Act
        settings1 = get_firecrawl_search_settings()
        settings2 = get_firecrawl_search_settings()

        # Assert
        assert settings1 is settings2


class TestJinaSearchSettings:
    """Test JinaSearchSettings class."""

    @pytest.mark.ai
    def test_jina_search_settings__creates_with_api_key__when_provided(self) -> None:
        """
        Purpose: Verify JinaSearchSettings creates correctly with API key and endpoints.
        Why this matters: Ensures proper structure for Jina search API configuration.
        Setup summary: Create JinaSearchSettings with api_key, assert value stored with default endpoints.
        """
        # Arrange
        api_key: str = "test-jina-key"

        # Act
        settings: JinaSearchSettings = JinaSearchSettings(api_key=api_key)

        # Assert
        assert settings.api_key == "test-jina-key"
        assert hasattr(settings, "search_api_endpoint")
        assert hasattr(settings, "reader_api_endpoint")

    @pytest.mark.ai
    def test_jina_search_settings__is_configured_returns_true__when_api_key_set(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns True when API key is set.
        Why this matters: Enables validation of complete Jina search API configuration.
        Setup summary: Create JinaSearchSettings with api_key, assert is_configured is True.
        """
        # Arrange & Act
        settings: JinaSearchSettings = JinaSearchSettings(api_key="key")

        # Assert
        assert settings.is_configured is True

    @pytest.mark.ai
    def test_jina_search_settings__is_configured_returns_false__when_api_key_missing(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns False when API key is missing.
        Why this matters: Ensures incomplete configurations are properly detected.
        Setup summary: Create JinaSearchSettings with None api_key, assert is_configured is False.
        """
        # Arrange & Act
        settings: JinaSearchSettings = JinaSearchSettings(api_key=None)

        # Assert
        assert settings.is_configured is False

    @pytest.mark.ai
    def test_get_jina_search_settings__returns_singleton__on_multiple_calls(
        self,
    ) -> None:
        """
        Purpose: Verify get_jina_search_settings returns same instance on multiple calls.
        Why this matters: Ensures singleton pattern for settings instance.
        Setup summary: Call get_jina_search_settings twice, assert same instance returned.
        """
        # Arrange & Act
        settings1 = get_jina_search_settings()
        settings2 = get_jina_search_settings()

        # Assert
        assert settings1 is settings2


class TestTavilySearchSettings:
    """Test TavilySearchSettings class."""

    @pytest.mark.ai
    def test_tavily_search_settings__creates_with_api_key__when_provided(self) -> None:
        """
        Purpose: Verify TavilySearchSettings creates correctly with API key.
        Why this matters: Ensures proper structure for Tavily search API configuration.
        Setup summary: Create TavilySearchSettings with api_key, assert value stored.
        """
        # Arrange
        api_key: str = "test-tavily-key"

        # Act
        settings: TavilySearchSettings = TavilySearchSettings(api_key=api_key)

        # Assert
        assert settings.api_key == "test-tavily-key"

    @pytest.mark.ai
    def test_tavily_search_settings__is_configured_returns_true__when_api_key_set(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns True when API key is set.
        Why this matters: Enables validation of complete Tavily search API configuration.
        Setup summary: Create TavilySearchSettings with api_key, assert is_configured is True.
        """
        # Arrange & Act
        settings: TavilySearchSettings = TavilySearchSettings(api_key="key")

        # Assert
        assert settings.is_configured is True

    @pytest.mark.ai
    def test_tavily_search_settings__is_configured_returns_false__when_api_key_missing(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns False when API key is missing.
        Why this matters: Ensures incomplete configurations are properly detected.
        Setup summary: Create TavilySearchSettings with None api_key, assert is_configured is False.
        """
        # Arrange & Act
        settings: TavilySearchSettings = TavilySearchSettings(api_key=None)

        # Assert
        assert settings.is_configured is False

    @pytest.mark.ai
    def test_get_tavily_search_settings__returns_singleton__on_multiple_calls(
        self,
    ) -> None:
        """
        Purpose: Verify get_tavily_search_settings returns same instance on multiple calls.
        Why this matters: Ensures singleton pattern for settings instance.
        Setup summary: Call get_tavily_search_settings twice, assert same instance returned.
        """
        # Arrange & Act
        settings1 = get_tavily_search_settings()
        settings2 = get_tavily_search_settings()

        # Assert
        assert settings1 is settings2


class TestBraveSearchSettings:
    """Test BraveSearchSettings class."""

    @pytest.mark.ai
    def test_brave_search_settings__creates_with_all_fields__when_provided(
        self,
    ) -> None:
        """
        Purpose: Verify BraveSearchSettings creates correctly with API key and endpoint.
        Why this matters: Ensures proper structure for Brave search API configuration.
        Setup summary: Create BraveSearchSettings with api_key and api_endpoint, assert all values stored.
        """
        # Arrange
        api_key: str = "test-brave-key"
        api_endpoint: str = "https://api.search.brave.com"

        # Act
        settings: BraveSearchSettings = BraveSearchSettings(
            api_key=api_key, api_endpoint=api_endpoint
        )

        # Assert
        assert settings.api_key == "test-brave-key"
        assert settings.api_endpoint == "https://api.search.brave.com"

    @pytest.mark.ai
    def test_brave_search_settings__is_configured_returns_true__when_api_key_set(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns True when API key is set.
        Why this matters: Enables validation of complete Brave search API configuration.
        Setup summary: Create BraveSearchSettings with api_key, assert is_configured is True.
        """
        # Arrange & Act
        settings: BraveSearchSettings = BraveSearchSettings(
            api_key="key", api_endpoint="endpoint"
        )

        # Assert
        assert settings.is_configured is True

    @pytest.mark.ai
    def test_brave_search_settings__is_configured_returns_false__when_api_key_missing(
        self,
    ) -> None:
        """
        Purpose: Verify is_configured property returns False when API key is missing.
        Why this matters: Ensures incomplete configurations are properly detected.
        Setup summary: Create BraveSearchSettings with None api_key, assert is_configured is False.
        """
        # Arrange & Act
        settings: BraveSearchSettings = BraveSearchSettings(
            api_key=None, api_endpoint="endpoint"
        )

        # Assert
        assert settings.is_configured is False

    @pytest.mark.ai
    def test_get_brave_search_settings__returns_singleton__on_multiple_calls(
        self,
    ) -> None:
        """
        Purpose: Verify get_brave_search_settings returns same instance on multiple calls.
        Why this matters: Ensures singleton pattern for settings instance.
        Setup summary: Call get_brave_search_settings twice, assert same instance returned.
        """
        # Arrange & Act
        settings1 = get_brave_search_settings()
        settings2 = get_brave_search_settings()

        # Assert
        assert settings1 is settings2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
