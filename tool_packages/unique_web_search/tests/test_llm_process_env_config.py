"""Tests for LLM processor environment-based configuration override logic."""

from unittest.mock import Mock, patch

import pytest

from unique_web_search.services.content_processing.processing_strategies.llm_process import (
    _DEFAULTS,
    LLMProcess,
    LLMProcessorConfig,
    _get_from_env,
    _merge_config_with_env,
    _should_disable_ui_config,
)

_MODULE = (
    "unique_web_search.services.content_processing.processing_strategies.llm_process"
)


# ---------------------------------------------------------------------------
# _should_disable_ui_config tests
# ---------------------------------------------------------------------------


class TestShouldDisableUiConfig:
    """Tests for the UI-disable flag driven by env config presence."""

    @pytest.mark.ai
    def test_should_disable_ui_config__returns_false__when_env_config_empty(
        self,
    ) -> None:
        """
        Purpose: Verify UI config is not disabled when no env override is set.
        Why this matters: Spaces admins must retain control when IT hasn't locked config.
        Setup summary: Patch _LLM_PROCESS_CONFIG to empty dict; assert False.
        """
        # Arrange
        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {}):
            # Act
            result = _should_disable_ui_config()

        # Assert
        assert result is False

    @pytest.mark.ai
    def test_should_disable_ui_config__returns_true__when_env_config_has_keys(
        self,
    ) -> None:
        """
        Purpose: Verify UI config is disabled when env override contains keys.
        Why this matters: IT admins expect UI fields to be frozen once env is set.
        Setup summary: Patch _LLM_PROCESS_CONFIG with one key; assert True.
        """
        # Arrange
        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {"enabled": True}):
            # Act
            result = _should_disable_ui_config()

        # Assert
        assert result is True


# ---------------------------------------------------------------------------
# _get_from_env tests
# ---------------------------------------------------------------------------


class TestGetFromEnv:
    """Tests for the env-config key lookup with snake_case/camelCase fallback."""

    @pytest.mark.ai
    def test_get_from_env__returns_default__when_config_empty(self) -> None:
        """
        Purpose: Verify default is returned when _LLM_PROCESS_CONFIG is empty.
        Why this matters: Ensures no-env-override path works correctly.
        Setup summary: Patch config to empty dict; call with default; assert default returned.
        """
        # Arrange
        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {}):
            # Act
            result = _get_from_env("enabled", False)

        # Assert
        assert result is False

    @pytest.mark.ai
    def test_get_from_env__returns_value__when_snake_case_key_exists(self) -> None:
        """
        Purpose: Verify value is returned for an exact snake_case key match.
        Why this matters: Python-style keys in env JSON must be respected.
        Setup summary: Patch config with snake_case key; assert env value returned.
        """
        # Arrange
        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {"min_tokens": 999}):
            # Act
            result = _get_from_env("min_tokens", 5000)

        # Assert
        assert result == 999

    @pytest.mark.ai
    def test_get_from_env__returns_value__when_camel_case_key_exists(self) -> None:
        """
        Purpose: Verify value is returned when only camelCase version of key exists.
        Why this matters: JSON from frontend/config may use camelCase naming.
        Setup summary: Patch config with camelCase key; assert env value returned.
        """
        # Arrange
        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {"minTokens": 1234}):
            # Act
            result = _get_from_env("min_tokens", 5000)

        # Assert
        assert result == 1234

    @pytest.mark.ai
    def test_get_from_env__prefers_snake_case__over_camel_case(self) -> None:
        """
        Purpose: Verify snake_case key takes precedence when both forms exist.
        Why this matters: Predictable resolution order prevents config surprises.
        Setup summary: Patch config with both key forms; assert snake_case value used.
        """
        # Arrange
        with patch(
            f"{_MODULE}._LLM_PROCESS_CONFIG",
            {"min_tokens": 111, "minTokens": 222},
        ):
            # Act
            result = _get_from_env("min_tokens", 5000)

        # Assert
        assert result == 111


# ---------------------------------------------------------------------------
# _DEFAULTS completeness test
# ---------------------------------------------------------------------------


class TestDefaultsCompleteness:
    """Tests verifying _DEFAULTS covers all LLMProcessorConfig fields."""

    @pytest.mark.ai
    def test_defaults__contains_all_config_fields__from_llm_processor_config(
        self,
    ) -> None:
        """
        Purpose: Verify every field in LLMProcessorConfig has a corresponding key in _DEFAULTS.
        Why this matters: Missing defaults would cause KeyError or fall through to Pydantic
            defaults, bypassing the env-override mechanism entirely.
        Setup summary: Compare LLMProcessorConfig.model_fields keys against _DEFAULTS keys.
        """
        # Arrange
        config_fields = set(LLMProcessorConfig.model_fields.keys())

        # Act
        defaults_keys = set(_DEFAULTS.keys())

        # Assert
        assert config_fields == defaults_keys, (
            f"Mismatch between LLMProcessorConfig fields and _DEFAULTS keys.\n"
            f"  In config but not in _DEFAULTS: {config_fields - defaults_keys}\n"
            f"  In _DEFAULTS but not in config: {defaults_keys - config_fields}"
        )


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
        Setup summary: Patch _LLM_PROCESS_CONFIG to empty; compare input/output configs.
        """
        # Arrange
        original = LLMProcessorConfig(enabled=True, min_tokens=3000)

        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {}):
            # Act
            merged = _merge_config_with_env(original)

        # Assert
        assert merged.enabled is True
        assert merged.min_tokens == 3000

    @pytest.mark.ai
    def test_merge__env_overrides_config_values__when_env_has_keys(self) -> None:
        """
        Purpose: Verify env config overrides space-admin config for matching keys.
        Why this matters: IT admins must be able to force settings across all spaces.
        Setup summary: Config has enabled=False; env has camelCase overrides; assert env wins.
        """
        # Arrange
        original = LLMProcessorConfig(enabled=False, min_tokens=5000)

        with patch(
            f"{_MODULE}._LLM_PROCESS_CONFIG", {"enabled": True, "minTokens": 100}
        ):
            # Act
            merged = _merge_config_with_env(original)

        # Assert
        assert merged.enabled is True
        assert merged.min_tokens == 100

    @pytest.mark.ai
    def test_merge__env_with_camel_case_keys__overrides_via_alias(self) -> None:
        """
        Purpose: Verify camelCase env keys properly override config through Pydantic alias.
        Why this matters: The config model uses aliases; env JSON may use camelCase.
        Setup summary: Env has camelCase key for minTokens; assert it overrides config.
        """
        # Arrange
        original = LLMProcessorConfig(min_tokens=5000)

        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {"minTokens": 42}):
            # Act
            merged = _merge_config_with_env(original)

        # Assert
        assert merged.min_tokens == 42

    @pytest.mark.ai
    def test_merge__partial_env__only_overrides_specified_keys(self) -> None:
        """
        Purpose: Verify only keys present in env are overridden, others keep config values.
        Why this matters: IT may only want to lock a subset of fields (e.g. sanitize only).
        Setup summary: Config has custom min_tokens; env only sets nested sanitize; assert min_tokens unchanged.
        """
        # Arrange
        original = LLMProcessorConfig(min_tokens=7777)

        with patch(
            f"{_MODULE}._LLM_PROCESS_CONFIG",
            {"privacy_filter": {"sanitize": True}},
        ):
            # Act
            merged = _merge_config_with_env(original)

        # Assert
        assert merged.privacy_filter.sanitize is True
        assert merged.min_tokens == 7777


# ---------------------------------------------------------------------------
# LLMProcessorConfig defaults tests
# ---------------------------------------------------------------------------


class TestLLMProcessorConfigDefaults:
    """Tests for LLMProcessorConfig default values sourced from _DEFAULTS."""

    @pytest.mark.ai
    def test_config__default_enabled__matches_defaults_dict(self) -> None:
        """
        Purpose: Verify LLMProcessorConfig default enabled value comes from _DEFAULTS.
        Why this matters: Ensures env-override mechanism is wired into the field defaults.
        Setup summary: Create default config; compare enabled to _DEFAULTS["enabled"].
        """
        # Act
        config = LLMProcessorConfig()

        # Assert
        assert config.enabled == _DEFAULTS["enabled"]

    @pytest.mark.ai
    def test_config__default_min_tokens__matches_defaults_dict(self) -> None:
        """
        Purpose: Verify LLMProcessorConfig default min_tokens comes from _DEFAULTS.
        Why this matters: Ensures env-override mechanism is wired into the field defaults.
        Setup summary: Create default config; compare min_tokens to _DEFAULTS["min_tokens"].
        """
        # Act
        config = LLMProcessorConfig()

        # Assert
        assert config.min_tokens == _DEFAULTS["min_tokens"]

    @pytest.mark.ai
    def test_config__default_sanitize__matches_defaults_dict(self) -> None:
        """
        Purpose: Verify LLMProcessorConfig default sanitize comes from _DEFAULTS.
        Why this matters: Ensures env-override mechanism is wired into the field defaults.
        Setup summary: Create default config; compare sanitize to _DEFAULTS privacy_filter entry.
        """
        # Act
        config = LLMProcessorConfig()

        # Assert
        assert config.privacy_filter.sanitize == _DEFAULTS["privacy_filter"]["sanitize"]

    @pytest.mark.ai
    def test_config__default_sanitize_rules__matches_defaults_dict(self) -> None:
        """
        Purpose: Verify LLMProcessorConfig default sanitize_rules comes from _DEFAULTS.
        Why this matters: Ensures env-override mechanism is wired into the field defaults.
        Setup summary: Create default config; compare sanitize_rules to _DEFAULTS privacy_filter entry.
        """
        # Act
        config = LLMProcessorConfig()

        # Assert
        assert (
            config.privacy_filter.sanitize_rules
            == _DEFAULTS["privacy_filter"]["sanitize_rules"]
        )

    @pytest.mark.ai
    def test_config__default_system_prompt__matches_defaults_dict(self) -> None:
        """
        Purpose: Verify LLMProcessorConfig default system_prompt comes from _DEFAULTS.
        Why this matters: Ensures env-override mechanism is wired into the field defaults.
        Setup summary: Create default config; compare system_prompt to _DEFAULTS prompts entry.
        """
        # Act
        config = LLMProcessorConfig()

        # Assert
        assert config.prompts.system_prompt == _DEFAULTS["prompts"]["system_prompt"]

    @pytest.mark.ai
    def test_config__default_user_prompt__matches_defaults_dict(self) -> None:
        """
        Purpose: Verify LLMProcessorConfig default user_prompt comes from _DEFAULTS.
        Why this matters: Ensures env-override mechanism is wired into the field defaults.
        Setup summary: Create default config; compare user_prompt to _DEFAULTS prompts entry.
        """
        # Act
        config = LLMProcessorConfig()

        # Assert
        assert config.prompts.user_prompt == _DEFAULTS["prompts"]["user_prompt"]


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
        Setup summary: Patch _merge_config_with_env; instantiate LLMProcess; assert it was called.
        """
        # Arrange
        config = LLMProcessorConfig(enabled=False)
        mock_llm_service = Mock()
        mock_encoder = Mock()
        mock_decoder = Mock()

        with patch(
            f"{_MODULE}._merge_config_with_env", wraps=_merge_config_with_env
        ) as mock_merge:
            # Act
            LLMProcess(
                config=config,
                llm_service=mock_llm_service,
                encoder=mock_encoder,
                decoder=mock_decoder,
            )

        # Assert
        mock_merge.assert_called_once_with(config)

    @pytest.mark.ai
    def test_init__env_override_reflected_in_is_enabled__when_env_sets_enabled(
        self,
    ) -> None:
        """
        Purpose: Verify env override of 'enabled' is reflected in LLMProcess.is_enabled.
        Why this matters: The runtime behavior must respect the env-forced config.
        Setup summary: Config has enabled=False; env has enabled=True; assert is_enabled is True.
        """
        # Arrange
        config = LLMProcessorConfig(enabled=False)
        mock_llm_service = Mock()
        mock_encoder = Mock()
        mock_decoder = Mock()

        with patch(f"{_MODULE}._LLM_PROCESS_CONFIG", {"enabled": True}):
            # Act
            processor = LLMProcess(
                config=config,
                llm_service=mock_llm_service,
                encoder=mock_encoder,
                decoder=mock_decoder,
            )

        # Assert
        assert processor.is_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
