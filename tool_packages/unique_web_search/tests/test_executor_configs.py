"""Tests for executor configs module."""

import pytest
from pydantic import ValidationError

from unique_web_search.services.executors.configs import (
    WebSearchMode,
    get_default_web_search_mode_config,
)
from unique_web_search.services.executors.configs.v2_config import WebSearchV2Config


class TestGetDefaultWebSearchModeConfig:
    """Test cases for get_default_web_search_mode_config function."""

    def test_get_default_web_search_mode_config_returns_v1(self, monkeypatch):
        """Test get_default_web_search_mode_config returns V1 when env is set to v1."""
        from unique_web_search import settings

        # Mock the env_settings to return v1
        monkeypatch.setattr(settings.env_settings, "web_search_mode", "v1")

        result = get_default_web_search_mode_config()

        assert result == WebSearchMode.V1

    def test_get_default_web_search_mode_config_returns_v2(self, monkeypatch):
        """Test get_default_web_search_mode_config returns V2 when env is set to v2."""
        from unique_web_search import settings

        # Mock the env_settings to return v2
        monkeypatch.setattr(settings.env_settings, "web_search_mode", "v2")

        result = get_default_web_search_mode_config()

        assert result == WebSearchMode.V2

    def test_get_default_web_search_mode_config_raises_error_for_invalid(
        self, monkeypatch
    ):
        """Test get_default_web_search_mode_config raises ValueError for invalid mode."""
        from unique_web_search import settings

        # Mock the env_settings to return an invalid mode
        monkeypatch.setattr(settings.env_settings, "web_search_mode", "v3")

        with pytest.raises(ValueError) as exc_info:
            get_default_web_search_mode_config()

        assert "Invalid web search mode" in str(exc_info.value)


class TestWebSearchV2ConfigModeValidator:
    """Test cases for WebSearchV2Config mode field validator."""

    def test_mode_validator_accepts_v2(self):
        """Test mode validator accepts 'v2' string."""
        config = WebSearchV2Config(mode="v2")
        assert config.mode == WebSearchMode.V2

    def test_mode_validator_accepts_v2_beta(self):
        """Test mode validator accepts 'v2 (beta)' string."""
        config = WebSearchV2Config(mode="v2 (beta)")
        assert config.mode == WebSearchMode.V2

    def test_mode_validator_accepts_uppercase_v2(self):
        """Test mode validator accepts uppercase 'V2' string."""
        config = WebSearchV2Config(mode="V2")
        assert config.mode == WebSearchMode.V2

    def test_mode_validator_accepts_uppercase_v2_beta(self):
        """Test mode validator accepts uppercase 'V2 (BETA)' string."""
        config = WebSearchV2Config(mode="V2 (BETA)")
        assert config.mode == WebSearchMode.V2

    def test_mode_validator_accepts_mixed_case_v2(self):
        """Test mode validator accepts mixed case 'V2 (Beta)' string."""
        config = WebSearchV2Config(mode="V2 (Beta)")
        assert config.mode == WebSearchMode.V2

    def test_mode_validator_accepts_any_string_with_v2(self):
        """Test mode validator accepts any string containing 'v2'."""
        config = WebSearchV2Config(mode="web search v2 mode")
        assert config.mode == WebSearchMode.V2

    def test_mode_validator_rejects_v1(self):
        """Test mode validator rejects 'v1' string."""
        with pytest.raises(ValidationError) as exc_info:
            WebSearchV2Config(mode="v1")
        assert "Invalid mode" in str(exc_info.value)

    def test_mode_validator_rejects_v3(self):
        """Test mode validator rejects 'v3' string."""
        with pytest.raises(ValidationError) as exc_info:
            WebSearchV2Config(mode="v3")
        assert "Invalid mode" in str(exc_info.value)

    def test_mode_validator_rejects_invalid_string(self):
        """Test mode validator rejects invalid mode string."""
        with pytest.raises(ValidationError) as exc_info:
            WebSearchV2Config(mode="invalid")
        assert "Invalid mode" in str(exc_info.value)

    def test_mode_validator_rejects_empty_string(self):
        """Test mode validator rejects empty string."""
        with pytest.raises(ValidationError) as exc_info:
            WebSearchV2Config(mode="")
        assert "Invalid mode" in str(exc_info.value)
