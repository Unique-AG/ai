"""Tests for processing strategies settings — field defaults and validation."""

import pytest

from unique_web_search.services.content_processing.processing_strategies.settings import (
    LLMProcessorEnvConfig,
    PrivacyFilterEnvConfig,
    ProcessingStrategiesSettings,
    SanitizeMode,
)


class TestSanitizeMode:
    """Test cases for SanitizeMode enum values and helpers."""

    @pytest.mark.ai
    def test_sanitize_mode__always_sanitize__has_correct_value(self) -> None:
        """
        Purpose: Verify SanitizeMode.ALWAYS_SANITIZE resolves to its string value.
        Why this matters: The env-var is compared against the string value at runtime.
        Setup summary: Check the enum member's string value.
        """
        assert SanitizeMode.ALWAYS_SANITIZE == "always_sanitize"

    @pytest.mark.ai
    def test_sanitize_mode__all_members__have_string_values(self) -> None:
        """
        Purpose: Verify every SanitizeMode member is a valid non-empty string.
        Why this matters: StrEnum members are used as discriminators in config parsing.
        Setup summary: Iterate all members and assert non-empty strings.
        """
        for member in SanitizeMode:
            assert isinstance(member.value, str)
            assert len(member.value) > 0

    @pytest.mark.ai
    def test_sanitize_mode__get_enum_names__length_matches_member_count(self) -> None:
        """
        Purpose: Verify get_enum_names() returns one label per enum member.
        Why this matters: The UI dropdown relies on a 1-to-1 alignment between values and labels.
        Setup summary: Compare list length against len(SanitizeMode).
        """
        assert len(SanitizeMode.get_enum_names()) == len(SanitizeMode)


class TestPrivacyFilterEnvConfig:
    """Test cases for PrivacyFilterEnvConfig defaults."""

    @pytest.mark.ai
    def test_sanitize__defaults_to_false(self) -> None:
        """
        Purpose: Verify sanitize defaults to False.
        Why this matters: Privacy filtering must be opt-in; default must never redact.
        Setup summary: Create default config; assert sanitize is False.
        """
        config = PrivacyFilterEnvConfig()

        assert config.sanitize is False

    @pytest.mark.ai
    def test_sanitize_mode__defaults_to_always_sanitize(self) -> None:
        """
        Purpose: Verify sanitize_mode defaults to ALWAYS_SANITIZE.
        Why this matters: When sanitize is toggled on, the default pipeline must be defined.
        Setup summary: Create default config; assert sanitize_mode is ALWAYS_SANITIZE.
        """
        config = PrivacyFilterEnvConfig()

        assert config.sanitize_mode == SanitizeMode.ALWAYS_SANITIZE

    @pytest.mark.ai
    def test_sanitize_mode__can_be_overridden(self) -> None:
        """
        Purpose: Verify sanitize_mode accepts all valid SanitizeMode values.
        Why this matters: Operators must be able to choose a different pipeline mode.
        Setup summary: Create config with each non-default mode; assert it is stored.
        """
        for mode in SanitizeMode:
            config = PrivacyFilterEnvConfig(sanitize_mode=mode)
            assert config.sanitize_mode == mode


class TestLLMProcessorEnvConfig:
    """Test cases for LLMProcessorEnvConfig defaults and custom values."""

    @pytest.mark.ai
    def test_enabled__defaults_to_false(self) -> None:
        """
        Purpose: Verify the LLM processor is disabled by default.
        Why this matters: Processor is an opt-in feature; must not run without explicit config.
        Setup summary: Create default config; assert enabled is False.
        """
        config = LLMProcessorEnvConfig()

        assert config.enabled is False

    @pytest.mark.ai
    def test_min_tokens__defaults_to_5000(self) -> None:
        """
        Purpose: Verify min_tokens threshold defaults to 5000.
        Why this matters: Content below this threshold skips LLM processing.
        Setup summary: Create default config; assert min_tokens is 5000.
        """
        config = LLMProcessorEnvConfig()

        assert config.min_tokens == 5000

    @pytest.mark.ai
    def test_privacy_filter__defaults_to_privacy_filter_env_config_instance(
        self,
    ) -> None:
        """
        Purpose: Verify privacy_filter is a PrivacyFilterEnvConfig with its own defaults.
        Why this matters: Nested config must be fully initialised, not None.
        Setup summary: Create default config; assert privacy_filter type and sanitize default.
        """
        config = LLMProcessorEnvConfig()

        assert isinstance(config.privacy_filter, PrivacyFilterEnvConfig)
        assert config.privacy_filter.sanitize is False

    @pytest.mark.ai
    def test_enabled__can_be_set_to_true(self) -> None:
        """
        Purpose: Verify enabled can be explicitly set to True.
        Why this matters: Operators enable the processor via the env-var JSON blob.
        Setup summary: Create config with enabled=True; assert value.
        """
        config = LLMProcessorEnvConfig(enabled=True)

        assert config.enabled is True

    @pytest.mark.ai
    def test_min_tokens__can_be_overridden(self) -> None:
        """
        Purpose: Verify min_tokens can be set to a custom value.
        Why this matters: Operators tune the threshold to match their content volume.
        Setup summary: Create config with custom min_tokens; assert value.
        """
        config = LLMProcessorEnvConfig(min_tokens=1000)

        assert config.min_tokens == 1000


class TestProcessingStrategiesSettings:
    """Test cases for ProcessingStrategiesSettings top-level defaults."""

    @pytest.mark.ai
    def test_llm_processor_config__defaults_to_llm_processor_env_config(self) -> None:
        """
        Purpose: Verify llm_processor_config is an LLMProcessorEnvConfig instance.
        Why this matters: The settings object must carry a fully-initialised nested config.
        Setup summary: Create default settings; assert nested config type.
        """
        settings = ProcessingStrategiesSettings()

        assert isinstance(settings.llm_processor_config, LLMProcessorEnvConfig)

    @pytest.mark.ai
    def test_llm_processor_config__enabled_defaults_to_false(self) -> None:
        """
        Purpose: Verify the processor is disabled out of the box at the settings level.
        Why this matters: Settings must not activate LLM processing without explicit opt-in.
        Setup summary: Create default settings; assert nested enabled field.
        """
        settings = ProcessingStrategiesSettings()

        assert settings.llm_processor_config.enabled is False
