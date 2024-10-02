from unique_toolkit.language_model import LanguageModel, LanguageModelName


def validate_and_init_language_model(value: LanguageModelName | LanguageModel | str):
    if isinstance(value, LanguageModel):
        return value

    return LanguageModel(value)
