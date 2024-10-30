from datetime import date

import pytest

from unique_toolkit.language_model.infos import (
    EncoderName,
    LanguageModel,
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
)


class TestLanguageModelInfos:
    def test_can_list_all_defined_models(self):
        models = LanguageModel.list_models()
        assert len(models) == 11
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
