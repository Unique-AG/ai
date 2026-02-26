"""Tests for WebSearchMode and related configuration changes."""

import os
from unittest.mock import patch

import pytest
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
    LanguageModelTokenLimits,
    ModelCapabilities,
)

from unique_web_search.config import WebSearchConfig
from unique_web_search.services.executors.configs import (
    WebSearchMode,
    get_default_web_search_mode_config,
)
from unique_web_search.settings import Base, Settings


class TestWebSearchModeEnum:
    """Test cases for WebSearchMode enum."""

    def test_web_search_mode_v1_value(self):
        """Test WebSearchMode.V1 has correct value."""
        assert WebSearchMode.V1 == "v1"
        assert WebSearchMode.V1.value == "v1"

    def test_web_search_mode_v2_value(self):
        """Test WebSearchMode.V2 has correct value."""
        assert WebSearchMode.V2 == "v2"
        assert WebSearchMode.V2.value == "v2"

    def test_web_search_mode_from_string_v1(self):
        """Test creating WebSearchMode from string 'v1'."""
        mode = WebSearchMode("v1")
        assert mode == WebSearchMode.V1

    def test_web_search_mode_from_string_v2(self):
        """Test creating WebSearchMode from string 'v2'."""
        mode = WebSearchMode("v2")
        assert mode == WebSearchMode.V2

    def test_web_search_mode_missing_alias_v2_beta_lowercase(self):
        """Test WebSearchMode._missing_ handles 'v2 (beta)' alias correctly."""
        mode = WebSearchMode("v2 (beta)")
        assert mode == WebSearchMode.V2

    def test_web_search_mode_missing_handles_invalid_value(self):
        """Test WebSearchMode raises ValueError for invalid values."""
        with pytest.raises(ValueError, match="'invalid' is not a valid WebSearchMode"):
            WebSearchMode("invalid")

    def test_web_search_mode_missing_handles_none(self):
        """Test WebSearchMode._missing_ handles None gracefully."""
        with pytest.raises(ValueError):
            WebSearchMode(None)  # type: ignore

    def test_web_search_mode_missing_handles_non_aliased_string(self):
        """Test WebSearchMode._missing_ returns None for non-aliased strings."""
        with pytest.raises(ValueError, match="'v3' is not a valid WebSearchMode"):
            WebSearchMode("v3")

    def test_web_search_mode_comparison(self):
        """Test WebSearchMode comparison operations."""
        assert WebSearchMode.V1 != WebSearchMode.V2
        assert WebSearchMode.V1 == "v1"
        assert WebSearchMode.V2 == "v2"


class TestGetDefaultWebSearchModeConfig:
    """Test cases for get_default_web_search_mode_config function."""

    def test_get_default_returns_v1_when_env_is_v1(self):
        """Test get_default_web_search_mode_config returns V1 when env is 'v1'."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = "v1"
            result = get_default_web_search_mode_config()
            assert result == WebSearchMode.V1

    def test_get_default_returns_v2_when_env_is_v2(self):
        """Test get_default_web_search_mode_config returns V2 when env is 'v2'."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = "v2"
            result = get_default_web_search_mode_config()
            assert result == WebSearchMode.V2

    def test_get_default_raises_error_for_invalid_mode(self):
        """Test get_default_web_search_mode_config raises ValueError for invalid mode."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = "invalid"
            with pytest.raises(ValueError, match="Invalid web search mode"):
                get_default_web_search_mode_config()

    def test_get_default_returns_web_search_mode_enum(self):
        """Test get_default_web_search_mode_config returns WebSearchMode enum."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = "v2"
            result = get_default_web_search_mode_config()
            assert isinstance(result, WebSearchMode)
            assert result == WebSearchMode.V2


class TestSettingsWebSearchMode:
    """Test cases for Settings.web_search_mode field."""

    def test_settings_web_search_mode_default_is_v2(self):
        """Test Settings.web_search_mode defaults to 'v2'."""
        # Create settings without environment variables
        with patch.dict(os.environ, {}, clear=True):
            settings = Base()
            assert settings.web_search_mode == "v2"

    def test_settings_web_search_mode_can_be_v1(self):
        """Test Settings.web_search_mode can be set to 'v1'."""
        settings = Base(web_search_mode="v1")
        assert settings.web_search_mode == "v1"

    def test_settings_web_search_mode_can_be_v2(self):
        """Test Settings.web_search_mode can be set to 'v2'."""
        settings = Base(web_search_mode="v2")
        assert settings.web_search_mode == "v2"

    def test_settings_web_search_mode_from_env(self):
        """Test Settings.web_search_mode can be loaded from environment."""
        with patch.dict(os.environ, {"WEB_SEARCH_MODE": "v1"}):
            settings = Settings()
            assert settings.web_search_mode == "v1"

    def test_settings_web_search_mode_is_required_field(self):
        """Test Settings.web_search_mode is a required field with default."""
        settings = Base()
        assert hasattr(settings, "web_search_mode")
        assert settings.web_search_mode is not None

    def test_settings_removed_default_web_search_mode_property(self):
        """Test Settings no longer has default_web_search_mode property."""
        settings = Base()
        # The property should no longer exist
        assert not hasattr(settings, "default_web_search_mode")


class TestWebSearchConfigDefaultMode:
    """Test cases for WebSearchConfig default web_search_active_mode."""

    @pytest.fixture
    def mock_language_model_info(self):
        """Mock LanguageModelInfo for testing."""
        return LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_4o_2024_1120,
            provider=LanguageModelProvider.AZURE,
            capabilities=[ModelCapabilities.STRUCTURED_OUTPUT],
            token_limits=LanguageModelTokenLimits(
                token_limit_input=128000, token_limit_output=4096
            ),
        )

    def test_web_search_config_default_mode_uses_env_setting(
        self, mock_language_model_info
    ):
        """Test WebSearchConfig.web_search_active_mode uses DEFAULT_WEB_SEARCH_MODE_CONFIG."""
        with patch(
            "unique_web_search.config.DEFAULT_WEB_SEARCH_MODE_CONFIG", WebSearchMode.V2
        ):
            config = WebSearchConfig(language_model=mock_language_model_info)
            assert config.web_search_active_mode == WebSearchMode.V2

    def test_web_search_config_default_mode_can_be_v1(self, mock_language_model_info):
        """Test WebSearchConfig.web_search_active_mode can default to V1."""
        # Explicitly set mode to V1 to test it can be V1
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode=WebSearchMode.V1,
        )
        assert config.web_search_active_mode == WebSearchMode.V1

    def test_web_search_config_mode_can_be_overridden(self, mock_language_model_info):
        """Test WebSearchConfig.web_search_active_mode can be overridden."""
        with patch(
            "unique_web_search.config.DEFAULT_WEB_SEARCH_MODE_CONFIG", WebSearchMode.V2
        ):
            config = WebSearchConfig(
                language_model=mock_language_model_info,
                web_search_active_mode=WebSearchMode.V1,
            )
            assert config.web_search_active_mode == WebSearchMode.V1

    def test_web_search_config_mode_selects_correct_config_v1(
        self, mock_language_model_info
    ):
        """Test WebSearchConfig.web_search_mode_config returns V1 config when mode is V1."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode=WebSearchMode.V1,
        )
        assert config.web_search_mode_config.mode == WebSearchMode.V1

    def test_web_search_config_mode_selects_correct_config_v2(
        self, mock_language_model_info
    ):
        """Test WebSearchConfig.web_search_mode_config returns V2 config when mode is V2."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode=WebSearchMode.V2,
        )
        assert config.web_search_mode_config.mode == WebSearchMode.V2

    def test_web_search_config_accepts_string_mode(self, mock_language_model_info):
        """Test WebSearchConfig accepts string values for web_search_active_mode."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode="v1",  # type: ignore
        )
        assert config.web_search_active_mode == WebSearchMode.V1

    def test_web_search_config_accepts_v2_beta_alias(self, mock_language_model_info):
        """Test WebSearchConfig accepts 'v2 (beta)' alias for web_search_active_mode."""
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode="v2 (beta)",  # type: ignore
        )
        assert config.web_search_active_mode == WebSearchMode.V2

    def test_web_search_config_rejects_invalid_mode(self, mock_language_model_info):
        """Test WebSearchConfig defaults to v1 for invalid web_search_active_mode values."""
        # The validator defaults to v1 for invalid values instead of raising an error
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode="invalid",  # type: ignore
        )
        assert config.web_search_active_mode == WebSearchMode.V1


class TestWebSearchModeIntegration:
    """Integration tests for WebSearchMode changes across the codebase."""

    @pytest.fixture
    def mock_language_model_info(self):
        """Mock LanguageModelInfo for testing."""
        return LanguageModelInfo(
            name=LanguageModelName.AZURE_GPT_4o_2024_1120,
            provider=LanguageModelProvider.AZURE,
            capabilities=[ModelCapabilities.STRUCTURED_OUTPUT],
            token_limits=LanguageModelTokenLimits(
                token_limit_input=128000, token_limit_output=4096
            ),
        )

    def test_settings_to_config_integration_v2(self, mock_language_model_info):
        """Test integration from Settings to WebSearchConfig with V2 mode."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = "v2"

            # Get the default mode
            default_mode = get_default_web_search_mode_config()
            assert default_mode == WebSearchMode.V2

            # Create config with this mode
            with patch(
                "unique_web_search.config.DEFAULT_WEB_SEARCH_MODE_CONFIG", default_mode
            ):
                config = WebSearchConfig(language_model=mock_language_model_info)
                assert config.web_search_active_mode == WebSearchMode.V2
                assert config.web_search_mode_config.mode == WebSearchMode.V2

    def test_settings_to_config_integration_v1(self, mock_language_model_info):
        """Test integration from Settings to WebSearchConfig with V1 mode."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = "v1"

            # Get the default mode
            default_mode = get_default_web_search_mode_config()
            assert default_mode == WebSearchMode.V1

            # Create config with explicitly set mode
            config = WebSearchConfig(
                language_model=mock_language_model_info,
                web_search_active_mode=default_mode,
            )
            assert config.web_search_active_mode == WebSearchMode.V1
            assert config.web_search_mode_config.mode == WebSearchMode.V1

    def test_backward_compatibility_with_v2_beta_string(self, mock_language_model_info):
        """Test backward compatibility with 'v2 (beta)' string in configs."""
        # This tests that existing configs with 'v2 (beta)' still work
        config = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode=WebSearchMode("v2 (beta)"),
        )
        assert config.web_search_active_mode == WebSearchMode.V2

    def test_mode_property_returns_correct_config_type(self, mock_language_model_info):
        """Test web_search_mode_config property returns correct config type."""
        config_v1 = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode=WebSearchMode.V1,
        )
        assert config_v1.web_search_mode_config == config_v1.web_search_mode_config_v1

        config_v2 = WebSearchConfig(
            language_model=mock_language_model_info,
            web_search_active_mode=WebSearchMode.V2,
        )
        assert config_v2.web_search_mode_config == config_v2.web_search_mode_config_v2


class TestWebSearchModeEdgeCases:
    """Test edge cases and error handling for WebSearchMode."""

    def test_web_search_mode_case_sensitivity(self):
        """Test WebSearchMode handles case-sensitive values correctly."""
        # Should work with lowercase
        mode = WebSearchMode("v1")
        assert mode == WebSearchMode.V1

        # Should fail with uppercase (StrEnum is case-sensitive by default)
        with pytest.raises(ValueError):
            WebSearchMode("V1")

    def test_web_search_mode_alias_case_sensitivity(self):
        """Test WebSearchMode._missing_ alias is case-sensitive."""
        # Should work with lowercase alias
        mode = WebSearchMode("v2 (beta)")
        assert mode == WebSearchMode.V2

        # Should fail with different case
        with pytest.raises(ValueError):
            WebSearchMode("V2 (Beta)")

    def test_get_default_with_none_mode(self):
        """Test get_default_web_search_mode_config handles None gracefully."""
        with patch(
            "unique_web_search.services.executors.configs.env_settings"
        ) as mock_settings:
            mock_settings.web_search_mode = None
            with pytest.raises((ValueError, AttributeError)):
                get_default_web_search_mode_config()

    def test_web_search_mode_serialization(self):
        """Test WebSearchMode serialization to string."""
        assert str(WebSearchMode.V1) == "v1"
        assert str(WebSearchMode.V2) == "v2"

    def test_web_search_mode_in_collection(self):
        """Test WebSearchMode in collections."""
        modes = [WebSearchMode.V1, WebSearchMode.V2]
        assert WebSearchMode.V1 in modes
        assert WebSearchMode.V2 in modes
        assert WebSearchMode("v1") in modes

    def test_web_search_mode_hash(self):
        """Test WebSearchMode can be used in sets and as dict keys."""
        mode_set = {WebSearchMode.V1, WebSearchMode.V2}
        assert len(mode_set) == 2

        mode_dict = {WebSearchMode.V1: "config1", WebSearchMode.V2: "config2"}
        assert mode_dict[WebSearchMode.V1] == "config1"
        assert mode_dict[WebSearchMode.V2] == "config2"
