from datetime import date

from unique_toolkit.language_model.infos import (
    LanguageModel,
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
)


class TestLanguageModelInfos:
    def test_can_list_all_models(self):
        models = LanguageModel.list_models()
        assert len(models) == 10
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
