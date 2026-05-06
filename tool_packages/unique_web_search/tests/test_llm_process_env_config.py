"""Tests for LLM processor environment-based configuration override logic."""

from unittest.mock import Mock, patch

import pytest

from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    LLMProcess,
    LLMProcessorConfig,
    PrivacyFilterConfig,
    PromptConfig,
    _merge_config_with_env,
)
from unique_web_search.services.content_processing.processing_strategies.settings import (
    DEFAULT_FLAG_MESSAGE,
    LLMProcessorEnvConfig,
    PrivacyFilterEnvConfig,
    ProcessingStrategiesSettings,
    PromptEnvConfig,
    SanitizeMode,
    processing_strategies_settings,
)

_PROCESS_MODULE = (
    "unique_web_search.services.content_processing.processing_strategies.llm_process"
)


# ---------------------------------------------------------------------------
# Structure-matching tests — env config mirrors UI config
# ---------------------------------------------------------------------------


class TestEnvConfigStructureMatchesUIConfig:
    """Verify that *EnvConfig field names exactly mirror the corresponding
    UI *Config models.  A mismatch would mean env overrides silently fail to
    reach the UI model or _merge_config_with_env produces KeyErrors.
    """

    @pytest.mark.ai
    def test_llm_processor_env_config__fields_match__llm_processor_config(
        self,
    ) -> None:
        """
        Purpose: Every field on LLMProcessorEnvConfig must exist on LLMProcessorConfig.
        Why this matters: _merge_config_with_env walks env_config.model_fields_set and
        writes into a LLMProcessorConfig dict — missing keys would raise or be ignored.
        """
        env_fields = set(LLMProcessorEnvConfig.model_fields.keys())
        config_fields = set(LLMProcessorConfig.model_fields.keys())

        assert env_fields == config_fields, (
            f"Field mismatch between LLMProcessorEnvConfig and LLMProcessorConfig.\n"
            f"  In env but not config: {env_fields - config_fields}\n"
            f"  In config but not env: {config_fields - env_fields}"
        )

    @pytest.mark.ai
    def test_privacy_filter_env_config__fields_match__privacy_filter_config(
        self,
    ) -> None:
        """
        Purpose: Every field on PrivacyFilterEnvConfig must exist on PrivacyFilterConfig.
        Why this matters: Nested merge iterates sub_model.model_fields_set — any drift
        means env overrides silently don't apply.
        """
        env_fields = set(PrivacyFilterEnvConfig.model_fields.keys())
        config_fields = set(PrivacyFilterConfig.model_fields.keys())

        assert env_fields == config_fields, (
            f"Field mismatch between PrivacyFilterEnvConfig and PrivacyFilterConfig.\n"
            f"  In env but not config: {env_fields - config_fields}\n"
            f"  In config but not env: {config_fields - env_fields}"
        )

    @pytest.mark.ai
    def test_prompt_env_config__fields_match__prompt_config(self) -> None:
        """
        Purpose: Every field on PromptEnvConfig must exist on PromptConfig.
        Why this matters: Same as above — nested merge requires 1:1 mapping.
        """
        env_fields = set(PromptEnvConfig.model_fields.keys())
        config_fields = set(PromptConfig.model_fields.keys())

        assert env_fields == config_fields, (
            f"Field mismatch between PromptEnvConfig and PromptConfig.\n"
            f"  In env but not config: {env_fields - config_fields}\n"
            f"  In config but not env: {config_fields - env_fields}"
        )

    @pytest.mark.ai
    def test_env_config__nested_sub_models_exist__on_config(self) -> None:
        """
        Purpose: Verify that every sub-model field on the env config has a
        matching field on the UI config.
        Why this matters: _merge_config_with_env iterates env sub-models and
        writes into the config dict — if a field name differs the merge breaks.
        """
        env_nested = {
            name
            for name, field in LLMProcessorEnvConfig.model_fields.items()
            if hasattr(field.default_factory, "model_fields")
            if field.default_factory is not None
        }

        for name in env_nested:
            assert name in LLMProcessorConfig.model_fields, (
                f"Env sub-model field '{name}' not found on LLMProcessorConfig"
            )


# ---------------------------------------------------------------------------
# LLMProcessorEnvConfig parsing tests
# ---------------------------------------------------------------------------


class TestLLMProcessorEnvConfig:
    """Tests for the typed env config model."""

    @pytest.mark.ai
    def test_env_config__defaults__when_no_overrides(self) -> None:
        """
        Purpose: Verify defaults are applied when no keys are provided.
        Why this matters: An empty env JSON must produce sensible defaults.
        """
        config = LLMProcessorEnvConfig()

        assert config.enabled is False
        assert config.min_tokens == 5000
        assert config.privacy_filter.sanitize is False
        assert config.privacy_filter.sanitize_mode == SanitizeMode.ALWAYS_SANITIZE
        assert config.privacy_filter.flag_message == DEFAULT_FLAG_MESSAGE
        assert config.model_fields_set == set()

    @pytest.mark.ai
    def test_env_config__tracks_fields_set__from_explicit_keys(self) -> None:
        """
        Purpose: Verify model_fields_set only contains explicitly provided keys.
        Why this matters: _merge_config_with_env relies on this to limit overrides.
        """
        config = LLMProcessorEnvConfig.model_validate(
            {"enabled": True, "minTokens": 100}
        )

        assert config.enabled is True
        assert config.min_tokens == 100
        assert "enabled" in config.model_fields_set
        assert "min_tokens" in config.model_fields_set
        assert "privacy_filter" not in config.model_fields_set

    @pytest.mark.ai
    def test_env_config__nested_privacy_filter__tracks_sub_fields_set(self) -> None:
        """
        Purpose: Verify nested model_fields_set works for privacy_filter sub-fields.
        Why this matters: The merge logic uses sub_model.model_fields_set for granular overrides.
        """
        config = LLMProcessorEnvConfig.model_validate(
            {"privacyFilter": {"sanitize": True}}
        )

        assert config.privacy_filter.sanitize is True
        assert "privacy_filter" in config.model_fields_set
        assert "sanitize" in config.privacy_filter.model_fields_set
        assert "sanitize_mode" not in config.privacy_filter.model_fields_set

    @pytest.mark.ai
    def test_env_config__accepts_snake_case_keys(self) -> None:
        """
        Purpose: Verify snake_case env JSON keys are accepted.
        Why this matters: Python-style keys in env JSON must be respected.
        """
        config = LLMProcessorEnvConfig.model_validate({"min_tokens": 999})

        assert config.min_tokens == 999

    @pytest.mark.ai
    def test_env_config__accepts_camel_case_keys(self) -> None:
        """
        Purpose: Verify camelCase env JSON keys are accepted through alias.
        Why this matters: JSON from frontend/config may use camelCase naming.
        """
        config = LLMProcessorEnvConfig.model_validate({"minTokens": 1234})

        assert config.min_tokens == 1234


# ---------------------------------------------------------------------------
# _merge_config_with_env tests
# ---------------------------------------------------------------------------


class TestMergeConfigWithEnv:
    """Tests for merging space-admin config with env overrides."""

    @pytest.mark.ai
    def test_merge__returns_unchanged_config__when_env_empty(self) -> None:
        """
        Purpose: Verify config passes through unmodified when no env override exists.
        Why this matters: Spaces without IT lockdown must keep their own settings.
        """
        original = LLMProcessorConfig(enabled=True, min_tokens=3000)
        env = LLMProcessorEnvConfig()

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            merged = _merge_config_with_env(original)

        assert merged.enabled is True
        assert merged.min_tokens == 3000

    @pytest.mark.ai
    def test_merge__env_overrides_top_level_values(self) -> None:
        """
        Purpose: Verify env config overrides space-admin config for top-level keys.
        Why this matters: IT admins must be able to force settings across all spaces.
        """
        original = LLMProcessorConfig(enabled=False, min_tokens=5000)
        env = LLMProcessorEnvConfig.model_validate({"enabled": True, "minTokens": 100})

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            merged = _merge_config_with_env(original)

        assert merged.enabled is True
        assert merged.min_tokens == 100

    @pytest.mark.ai
    def test_merge__env_overrides_nested_privacy_filter_fields(self) -> None:
        """
        Purpose: Verify nested env keys correctly override nested privacy_filter fields.
        Why this matters: This was the original bug — flat 'sanitize' key was lost.
        """
        original = LLMProcessorConfig(min_tokens=7777)
        env = LLMProcessorEnvConfig.model_validate(
            {"privacyFilter": {"sanitize": True}}
        )

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            merged = _merge_config_with_env(original)

        assert merged.privacy_filter.sanitize is True
        assert merged.min_tokens == 7777

    @pytest.mark.ai
    def test_merge__partial_env__only_overrides_specified_keys(self) -> None:
        """
        Purpose: Verify only keys present in env are overridden, others keep config values.
        Why this matters: IT may only want to lock a subset of fields.
        """
        original = LLMProcessorConfig(min_tokens=7777)
        env = LLMProcessorEnvConfig.model_validate(
            {"privacyFilter": {"sanitize": True, "sanitizeMode": "judge_only"}}
        )

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            merged = _merge_config_with_env(original)

        assert merged.privacy_filter.sanitize is True
        assert merged.privacy_filter.sanitize_mode == SanitizeMode.JUDGE_ONLY
        assert merged.min_tokens == 7777
        assert merged.privacy_filter.flag_message == DEFAULT_FLAG_MESSAGE

    @pytest.mark.ai
    def test_merge__single_nested_field__does_not_clobber_sibling_fields(self) -> None:
        """
        Purpose: Verify that setting ONE field inside privacy_filter does not
        reset its sibling fields to defaults (exclude_unset=True is recursive).
        Why this matters: The IT admin writes {"privacyFilter": {"sanitize": true}}
        and expects flag_message / sanitize_rules / sanitize_mode to stay as the
        space-admin configured them.
        """
        custom_flag = "CUSTOM FLAG FROM SPACE ADMIN"
        original = LLMProcessorConfig(
            privacy_filter=PrivacyFilterConfig(
                sanitize=False,
                flag_message=custom_flag,
                sanitize_mode=SanitizeMode.JUDGE_AND_SANITIZE,
            ),
        )
        env = LLMProcessorEnvConfig.model_validate(
            {"privacyFilter": {"sanitize": True}}
        )

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            merged = _merge_config_with_env(original)

        assert merged.privacy_filter.sanitize is True
        assert merged.privacy_filter.flag_message == custom_flag
        assert merged.privacy_filter.sanitize_mode == SanitizeMode.JUDGE_AND_SANITIZE

    @pytest.mark.ai
    def test_merge__env_prompt_override__only_overrides_specified_prompt(self) -> None:
        """
        Purpose: Verify a single prompt field override doesn't clobber other prompts.
        """
        original = LLMProcessorConfig()
        original_user_prompt = original.prompts.user_prompt
        env = LLMProcessorEnvConfig.model_validate(
            {"prompts": {"systemPrompt": "custom system"}}
        )

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            merged = _merge_config_with_env(original)

        assert merged.prompts.system_prompt == "custom system"
        assert merged.prompts.user_prompt == original_user_prompt


# ---------------------------------------------------------------------------
# LLMProcessorConfig defaults tests
# ---------------------------------------------------------------------------


class TestLLMProcessorConfigDefaults:
    """Tests for LLMProcessorConfig default values sourced from env settings."""

    @pytest.mark.ai
    def test_config__default_enabled__matches_env_config(self) -> None:
        config = LLMProcessorConfig()

        assert (
            config.enabled
            == processing_strategies_settings.llm_processor_config.enabled
        )

    @pytest.mark.ai
    def test_config__default_min_tokens__matches_env_config(self) -> None:
        config = LLMProcessorConfig()

        assert (
            config.min_tokens
            == processing_strategies_settings.llm_processor_config.min_tokens
        )

    @pytest.mark.ai
    def test_config__default_sanitize__matches_env_config(self) -> None:
        config = LLMProcessorConfig()

        assert (
            config.privacy_filter.sanitize
            == processing_strategies_settings.llm_processor_config.privacy_filter.sanitize
        )

    @pytest.mark.ai
    def test_config__default_sanitize_rules__matches_env_config(self) -> None:
        config = LLMProcessorConfig()

        assert (
            config.privacy_filter.sanitize_rules
            == processing_strategies_settings.llm_processor_config.privacy_filter.sanitize_rules
        )

    @pytest.mark.ai
    def test_config__default_system_prompt__matches_env_config(self) -> None:
        config = LLMProcessorConfig()

        assert (
            config.prompts.system_prompt
            == processing_strategies_settings.llm_processor_config.prompts.system_prompt
        )

    @pytest.mark.ai
    def test_config__default_user_prompt__matches_env_config(self) -> None:
        config = LLMProcessorConfig()

        assert (
            config.prompts.user_prompt
            == processing_strategies_settings.llm_processor_config.prompts.user_prompt
        )


# ---------------------------------------------------------------------------
# LLMProcess.__init__ env merge tests
# ---------------------------------------------------------------------------


class TestLLMProcessInitEnvMerge:
    """Tests for LLMProcess constructor applying _merge_config_with_env."""

    @pytest.mark.ai
    def test_init__merges_config_with_env__in_constructor(self) -> None:
        """
        Purpose: Verify LLMProcess.__init__ calls _merge_config_with_env on the config.
        Why this matters: Without this call, env overrides would not take effect at runtime.
        """
        config = LLMProcessorConfig(enabled=False)
        mock_llm_service = Mock()
        mock_encoder = Mock()
        mock_decoder = Mock()

        with patch(
            f"{_PROCESS_MODULE}._merge_config_with_env", wraps=_merge_config_with_env
        ) as mock_merge:
            LLMProcess(
                config=config,
                llm_service=mock_llm_service,
                encoder=mock_encoder,
                decoder=mock_decoder,
            )

        mock_merge.assert_called_once_with(config)

    @pytest.mark.ai
    def test_init__env_override_reflected_in_is_enabled(self) -> None:
        """
        Purpose: Verify env override of 'enabled' is reflected in LLMProcess.is_enabled.
        Why this matters: The runtime behavior must respect the env-forced config.
        """
        config = LLMProcessorConfig(enabled=False)
        mock_llm_service = Mock()
        mock_encoder = Mock()
        mock_decoder = Mock()
        env = LLMProcessorEnvConfig.model_validate({"enabled": True})

        with patch(
            f"{_PROCESS_MODULE}.processing_strategies_settings",
            ProcessingStrategiesSettings(llm_processor_config=env),
        ):
            processor = LLMProcess(
                config=config,
                llm_service=mock_llm_service,
                encoder=mock_encoder,
                decoder=mock_decoder,
            )

        assert processor.is_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
