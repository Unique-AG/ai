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
            LanguageModelName.AZURE_o3_2025_0416,
            LanguageModelName.AZURE_o4_MINI_2025_0416,
            LanguageModelName.ANTHROPIC_CLAUDE_3_7_SONNET,
            LanguageModelName.ANTHROPIC_CLAUDE_3_7_SONNET_THINKING,
            LanguageModelName.GEMINI_2_0_FLASH,
            LanguageModelName.GEMINI_2_5_FLASH_PREVIEW_0417,
            LanguageModelName.GEMINI_2_5_PRO_EXP_0325,
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
        assert model.retirement_at is None
        assert model.deprecated_at is None
        assert model.retirement_text is None

    def test_get_language_model_returns_custom_model_for_string(self):
        name = "custom"
        LanguageModel(name) == LanguageModelInfo(
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
        limits = LanguageModelTokenLimits(token_limit=10000)
        assert limits.token_limit_input == 4000
        assert limits.token_limit_output == 6000

    def test_language_model_token_limits_with_total_and_fraction(self):
        limits = LanguageModelTokenLimits(token_limit=10000, fraction_input=0.2)
        assert isinstance(limits.token_limit_input, int)
        assert isinstance(limits.token_limit_output, int)
        assert limits.token_limit_input == 2000
        assert limits.token_limit_output == 8000

    def test_language_model_token_limits_raises_error_empty(self):
        with pytest.raises(ValueError):
            LanguageModelTokenLimits()

    def test_rounding_does_not_exceed_token_limit(self):
        limits = LanguageModelTokenLimits(token_limit=2000, fraction_input=0.47)
        assert isinstance(limits.token_limit_input, int)
        assert isinstance(limits.token_limit_output, int)
        assert isinstance(limits.token_limit, int)
        assert (
            limits.token_limit_input + limits.token_limit_output <= limits.token_limit
        )

    def test_language_model_token_limits_raises_error_for_partial_input(self):
        with pytest.raises(ValueError):
            LanguageModelTokenLimits(token_limit_input=1000)

        with pytest.raises(ValueError):
            LanguageModelTokenLimits(token_limit_output=1000)

        with pytest.raises(ValueError):
            LanguageModelTokenLimits(fraction_input=0.5)

        with pytest.raises(ValueError):
            LanguageModelTokenLimits(token_limit_input=1000, fraction_input=0.5)
