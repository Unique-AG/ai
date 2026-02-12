import json
import os
from datetime import date
from unittest.mock import patch

import pytest

from unique_toolkit.language_model.infos import (
    EncoderName,
    LanguageModel,
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
)
from unique_toolkit.language_model.schemas import LanguageModelTokenLimits


class TestLanguageModelInfos:
    def test_can_list_all_defined_models(self):
        models = LanguageModel.list_models()
        expected_models = [
            LanguageModelName.AZURE_GPT_35_TURBO_0125,
            LanguageModelName.AZURE_GPT_4_0613,
            LanguageModelName.AZURE_GPT_4_32K_0613,
            LanguageModelName.AZURE_GPT_4_TURBO_2024_0409,
            LanguageModelName.AZURE_GPT_4o_2024_0513,
            LanguageModelName.AZURE_GPT_4o_2024_0806,
            LanguageModelName.AZURE_GPT_4o_2024_1120,
            LanguageModelName.AZURE_GPT_4o_MINI_2024_0718,
            LanguageModelName.AZURE_o1_MINI_2024_0912,
            LanguageModelName.AZURE_o1_2024_1217,
            LanguageModelName.AZURE_o3_MINI_2025_0131,
            LanguageModelName.AZURE_GPT_45_PREVIEW_2025_0227,
            LanguageModelName.AZURE_GPT_41_2025_0414,
            LanguageModelName.AZURE_GPT_41_MINI_2025_0414,
            LanguageModelName.AZURE_GPT_41_NANO_2025_0414,
            LanguageModelName.AZURE_o3_2025_0416,
            LanguageModelName.AZURE_o4_MINI_2025_0416,
            LanguageModelName.AZURE_MODEL_ROUTER_2025_1118,
            LanguageModelName.ANTHROPIC_CLAUDE_3_7_SONNET,
            LanguageModelName.ANTHROPIC_CLAUDE_3_7_SONNET_THINKING,
            LanguageModelName.ANTHROPIC_CLAUDE_HAIKU_4_5,
            LanguageModelName.ANTHROPIC_CLAUDE_SONNET_4,
            LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4,
            LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4_1,
            LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4_5,
            LanguageModelName.ANTHROPIC_CLAUDE_SONNET_4_5,
            LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4_6,
            LanguageModelName.GEMINI_2_0_FLASH,
            LanguageModelName.GEMINI_2_5_FLASH,
            LanguageModelName.GEMINI_2_5_FLASH_LITE,
            LanguageModelName.GEMINI_2_5_FLASH_LITE_PREVIEW_0617,
            LanguageModelName.GEMINI_2_5_FLASH_PREVIEW_0520,
            LanguageModelName.GEMINI_2_5_PRO,
            LanguageModelName.GEMINI_2_5_PRO_EXP_0325,
            LanguageModelName.GEMINI_2_5_PRO_PREVIEW_0605,
            LanguageModelName.GEMINI_3_FLASH_PREVIEW,
            LanguageModelName.GEMINI_3_PRO_PREVIEW,
            LanguageModelName.GROK_4_1_FAST_NON_REASONING,
            LanguageModelName.GROK_4_1_FAST_REASONING,
            LanguageModelName.AZURE_GPT_5_2025_0807,
            LanguageModelName.AZURE_GPT_5_MINI_2025_0807,
            LanguageModelName.AZURE_GPT_5_NANO_2025_0807,
            LanguageModelName.AZURE_GPT_5_CHAT_2025_0807,
            LanguageModelName.AZURE_GPT_5_PRO_2025_1006,
            LanguageModelName.AZURE_GPT_51_2025_1113,
            LanguageModelName.AZURE_GPT_51_THINKING_2025_1113,
            LanguageModelName.AZURE_GPT_51_CHAT_2025_1113,
            LanguageModelName.AZURE_GPT_51_CODEX_2025_1113,
            LanguageModelName.AZURE_GPT_51_CODEX_MINI_2025_1113,
            LanguageModelName.AZURE_GPT_52_2025_1211,
            LanguageModelName.AZURE_GPT_52_CHAT_2025_1211,
            LanguageModelName.LITELLM_OPENAI_GPT_5,
            LanguageModelName.LITELLM_OPENAI_GPT_5_MINI,
            LanguageModelName.LITELLM_OPENAI_GPT_5_NANO,
            LanguageModelName.LITELLM_OPENAI_GPT_5_CHAT,
            LanguageModelName.LITELLM_OPENAI_GPT_5_PRO,
            LanguageModelName.LITELLM_OPENAI_GPT_51,
            LanguageModelName.LITELLM_OPENAI_GPT_51_THINKING,
            LanguageModelName.LITELLM_OPENAI_GPT_52,
            LanguageModelName.LITELLM_OPENAI_GPT_52_THINKING,
            LanguageModelName.LITELLM_DEEPSEEK_R1,
            LanguageModelName.LITELLM_DEEPSEEK_V3,
            LanguageModelName.LITELLM_QWEN_3,
            LanguageModelName.LITELLM_QWEN_3_THINKING,
            LanguageModelName.LITELLM_OPENAI_O1,
            LanguageModelName.LITELLM_OPENAI_O3,
            LanguageModelName.LITELLM_OPENAI_O3_DEEP_RESEARCH,
            LanguageModelName.LITELLM_OPENAI_O3_PRO,
            LanguageModelName.LITELLM_OPENAI_O4_MINI,
            LanguageModelName.LITELLM_OPENAI_O4_MINI_DEEP_RESEARCH,
            LanguageModelName.LITELLM_OPENAI_GPT_4_1_MINI,
            LanguageModelName.LITELLM_OPENAI_GPT_4_1_NANO,
        ]
        assert len(models) == len(expected_models)
        assert all(isinstance(model, LanguageModelInfo) for model in models)
        assert all(model.name for model in models)
        model_names = [model.name for model in models]
        for model_name in expected_models:
            assert model_name in model_names

    def test_get_custom_language_model(self):
        model = LanguageModel("My Custom Model")

        assert model.name == "My Custom Model"
        assert model.provider == LanguageModelProvider.CUSTOM
        assert model.version == "custom"
        assert model.published_at is None
        assert model.info_cutoff_at is None
        assert model.encoder_name == EncoderName.CL100K_BASE
        assert model.token_limit_input == 7_000
        assert model.token_limit_output == 1_000
        assert model.token_limit == 8_000
        assert model.retirement_at == date(2225, 12, 31)
        assert model.deprecated_at == date(2225, 12, 31)
        assert model.retirement_text == "This model is no longer supported."

    def test_get_language_model_returns_custom_model_for_string(self):
        name = "custom"
        assert LanguageModel(name).info == LanguageModelInfo(
            name=name,
            version="custom",
            provider=LanguageModelProvider.CUSTOM,
        )

    # New tests for LanguageModelTokenLimits
    def test_language_model_token_limits_with_input_output(self):
        test_cases = [
            {
                "input": 2000,
                "output": 2000,
                "expected_total": 4000,
                "expected_fraction": 0.5,
            },
            {
                "input": 3000,
                "output": 1000,
                "expected_total": 4000,
                "expected_fraction": 0.75,
            },
            {
                "input": 1000,
                "output": 3000,
                "expected_total": 4000,
                "expected_fraction": 0.25,
            },
        ]

        for case in test_cases:
            limits = LanguageModelTokenLimits(
                token_limit_input=case["input"], token_limit_output=case["output"]
            )
            assert limits.token_limit == case["expected_total"]

    def test_language_model_token_limits_with_total(self):
        limits = LanguageModelTokenLimits(token_limit=10000)  # type: ignore[call-arg]
        assert limits.token_limit_input == 4000
        assert limits.token_limit_output == 6000

    def test_language_model_token_limits_with_total_and_fraction(self):
        limits = LanguageModelTokenLimits(token_limit=10000, fraction_input=0.2)  # type: ignore[call-arg]
        assert isinstance(limits.token_limit_input, int)
        assert isinstance(limits.token_limit_output, int)
        assert limits.token_limit_input == 2000
        assert limits.token_limit_output == 8000

    def test_language_model_token_limits_raises_error_empty(self):
        with pytest.raises(ValueError):
            LanguageModelTokenLimits()  # type: ignore[call-arg]

    def test_rounding_does_not_exceed_token_limit(self):
        limits = LanguageModelTokenLimits(token_limit=2000, fraction_input=0.47)  # type: ignore[call-arg]
        assert isinstance(limits.token_limit_input, int)
        assert isinstance(limits.token_limit_output, int)
        assert isinstance(limits.token_limit, int)
        assert (
            limits.token_limit_input + limits.token_limit_output <= limits.token_limit
        )

    def test_language_model_token_limits_raises_error_for_partial_input(self):
        with pytest.raises(ValueError):
            LanguageModelTokenLimits(token_limit_input=1000)  # type: ignore[call-arg]

        with pytest.raises(ValueError):
            LanguageModelTokenLimits(token_limit_output=1000)  # type: ignore[call-arg]

        with pytest.raises(ValueError):
            LanguageModelTokenLimits(fraction_input=0.5)  # type: ignore[call-arg]

        with pytest.raises(ValueError):
            LanguageModelTokenLimits(token_limit_input=1000, fraction_input=0.5)  # type: ignore[call-arg]


class TestLoadLanguageModelInfosFromEnv:
    """Tests for the _load_from_env classmethod."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear the lru_cache before and after each test."""
        LanguageModelInfo._load_from_env.cache_clear()
        yield
        LanguageModelInfo._load_from_env.cache_clear()

    @patch.dict(os.environ, {}, clear=True)
    def test_returns_empty_dict_when_env_not_set(self):
        result = LanguageModelInfo._load_from_env()
        assert result == {}

    def test_returns_empty_dict_when_env_is_empty(self):
        with patch.dict(os.environ, {LanguageModelInfo._ENV_VAR: ""}):
            result = LanguageModelInfo._load_from_env()
            assert result == {}

    def test_returns_empty_dict_on_invalid_json(self):
        with patch.dict(os.environ, {LanguageModelInfo._ENV_VAR: "not valid json"}):
            result = LanguageModelInfo._load_from_env()
            assert result == {}

    def test_returns_empty_dict_when_json_is_list(self):
        with patch.dict(os.environ, {LanguageModelInfo._ENV_VAR: '["a", "b", "c"]'}):
            result = LanguageModelInfo._load_from_env()
            assert result == {}

    def test_returns_empty_dict_when_json_is_string(self):
        with patch.dict(os.environ, {LanguageModelInfo._ENV_VAR: '"just a string"'}):
            result = LanguageModelInfo._load_from_env()
            assert result == {}

    def test_loads_single_model_info(self):
        model_infos = {
            "AZURE_GPT_4o_CUSTOM": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            result = LanguageModelInfo._load_from_env()
            assert result == model_infos
            assert "AZURE_GPT_4o_CUSTOM" in result
            assert result["AZURE_GPT_4o_CUSTOM"]["name"] == "AZURE_GPT_4o_2024_1120"

    def test_loads_multiple_model_infos(self):
        model_infos = {
            "AZURE_GPT_4o_CUSTOM": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            },
            "AZURE_GPT_4o_2024_1120_1234": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            },
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            result = LanguageModelInfo._load_from_env()
            assert len(result) == 2
            assert "AZURE_GPT_4o_CUSTOM" in result
            assert "AZURE_GPT_4o_2024_1120_1234" in result

    def test_skips_invalid_model_info_entries(self):
        model_infos = {
            "VALID_MODEL": {"name": "valid", "provider": "AZURE"},
            "INVALID_MODEL": "not a dict",
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            result = LanguageModelInfo._load_from_env()
            assert len(result) == 1
            assert "VALID_MODEL" in result
            assert "INVALID_MODEL" not in result

    def test_key_is_used_for_lookup_not_name_field(self):
        # The key in the dict should be used for lookup, not the "name" field inside
        model_infos = {
            "MY_CUSTOM_KEY": {
                "name": "DIFFERENT_NAME",
                "provider": "AZURE",
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            result = LanguageModelInfo._load_from_env()
            assert "MY_CUSTOM_KEY" in result
            assert "DIFFERENT_NAME" not in result


class TestLanguageModelInfoFromEnv:
    """Tests for from_name using environment variable."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear the lru_cache before and after each test."""
        LanguageModelInfo._load_from_env.cache_clear()
        yield
        LanguageModelInfo._load_from_env.cache_clear()

    def test_from_name_uses_env_model_info_when_key_matches(self):
        """Test that LanguageModelInfo.from_name uses env model info when key matches."""
        model_infos = {
            "AZURE_GPT_4o_2024_1120": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom-version",
                "token_limits": {"token_limit_input": 5000, "token_limit_output": 500},
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            model = LanguageModelInfo.from_name(
                LanguageModelName.AZURE_GPT_4o_2024_1120
            )
            assert model.version == "custom-version"
            assert model.token_limits.token_limit_input == 5000
            assert model.token_limits.token_limit_output == 500

    def test_from_name_env_takes_precedence_over_default(self):
        """Test that env model info takes precedence over built-in defaults."""
        # Override a built-in model with custom token limits
        model_infos = {
            "AZURE_GPT_4o_2024_1120": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "overridden",
                "token_limits": {"token_limit_input": 1000, "token_limit_output": 100},
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            model = LanguageModelInfo.from_name(
                LanguageModelName.AZURE_GPT_4o_2024_1120
            )
            # Should use env values, not defaults
            assert model.version == "overridden"
            assert model.token_limits.token_limit_input == 1000
            assert model.token_limits.token_limit_output == 100

    def test_from_name_falls_back_to_default_when_key_not_in_env(self):
        """Test that from_name falls back to default when model not in env."""
        model_infos = {
            "SOME_OTHER_MODEL": {
                "name": "SOME_OTHER_MODEL",
                "provider": "AZURE",
                "version": "custom",
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            model = LanguageModelInfo.from_name(
                LanguageModelName.AZURE_GPT_4o_2024_1120
            )
            # Should use default values since the key doesn't match
            assert model.version == "2024-11-20"

    def test_language_model_uses_env_model_info(self):
        """Test that LanguageModel wrapper also uses env model info."""
        model_infos = {
            "AZURE_GPT_4o_2024_1120": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "env-version",
                "token_limits": {"token_limit_input": 2000, "token_limit_output": 200},
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            model = LanguageModel(LanguageModelName.AZURE_GPT_4o_2024_1120)
            assert model.version == "env-version"
            assert model.token_limit_input == 2000
            assert model.token_limit_output == 200

    def test_env_model_with_custom_key(self):
        """Test loading model with a custom key that differs from the name field."""
        model_infos = {
            "MY_CUSTOM_GPT4o": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom-deployment",
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 300},
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            # Looking up by the key, not by the name field inside
            model = LanguageModelInfo.from_name("MY_CUSTOM_GPT4o")
            assert model.name == "AZURE_GPT_4o_2024_1120"
            assert model.version == "custom-deployment"
            assert model.token_limits.token_limit_input == 3000

    def test_env_model_with_all_capabilities(self):
        """Test loading model with full configuration from env."""
        model_infos = {
            "AZURE_GPT_4o_CUSTOM": {
                "name": "AZURE_GPT_4o_2024_1120",
                "provider": "AZURE",
                "version": "custom",
                "capabilities": ["function_calling", "streaming", "vision"],
                "token_limits": {"token_limit_input": 3000, "token_limit_output": 150},
            }
        }
        with patch.dict(
            os.environ, {LanguageModelInfo._ENV_VAR: json.dumps(model_infos)}
        ):
            model = LanguageModelInfo.from_name("AZURE_GPT_4o_CUSTOM")
            assert model.name == "AZURE_GPT_4o_2024_1120"
            assert model.provider == LanguageModelProvider.AZURE
            assert model.version == "custom"
            assert model.token_limits.token_limit_input == 3000
            assert model.token_limits.token_limit_output == 150
