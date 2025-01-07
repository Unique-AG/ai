from datetime import date

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
        assert len(models) == 12
        assert all(isinstance(model, LanguageModelInfo) for model in models)
        assert all(model.name for model in models)

        model_names = [model.name for model in models]
        assert LanguageModelName.AZURE_GPT_4_TURBO_1106 in model_names
        assert LanguageModelName.AZURE_GPT_4_TURBO_2024_0409 in model_names
        assert LanguageModelName.AZURE_GPT_4_VISION_PREVIEW in model_names
        assert LanguageModelName.AZURE_GPT_4_32K_0613 in model_names
        assert LanguageModelName.AZURE_GPT_4_0613 in model_names
        assert LanguageModelName.AZURE_GPT_35_TURBO_16K in model_names
        assert LanguageModelName.AZURE_GPT_35_TURBO in model_names
        assert LanguageModelName.AZURE_GPT_35_TURBO_0613 in model_names
        assert LanguageModelName.AZURE_GPT_35_TURBO_0125 in model_names
        assert LanguageModelName.AZURE_GPT_4o_2024_0513 in model_names
        assert LanguageModelName.AZURE_GPT_4o_2024_0806 in model_names
        assert LanguageModelName.AZURE_GPT_4o_MINI_2024_0718 in model_names

    def test_get_language_model(self):
        model = LanguageModel(LanguageModelName.AZURE_GPT_4_TURBO_1106)

        assert model.name == LanguageModelName.AZURE_GPT_4_TURBO_1106
        assert model.provider == LanguageModelProvider.AZURE
        assert model.version == "1106-preview"
        assert model.published_at == date(2023, 11, 6)
        assert model.info_cutoff_at == date(2023, 4, 1)
        assert model.token_limit_input == 128000
        assert model.token_limit_output == 4096
        assert model.token_limit == 128000 + 4096
        assert model.encoder_name == EncoderName.CL100K_BASE

    def test_get_custom_language_model(self):
        model = LanguageModel("My Custom Model")

        assert model.name == "My Custom Model"
        assert model.provider == LanguageModelProvider.CUSTOM
        assert model.version == "custom"
        assert model.published_at is None
        assert model.info_cutoff_at is None
        assert model.encoder_name is None
        assert model.token_limit_input is None
        assert model.token_limit_output is None
        assert model.token_limit is None
        assert model.retirement_at is None
        assert model.deprecated_at is None
        assert model.retirement_text is None

    def test_get_language_model_raises_error_for_invalid_model(self):
        with pytest.raises(ValueError):
            LanguageModel("")

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
            assert abs(limits.fraction_input - case["expected_fraction"]) < 1e-10

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
