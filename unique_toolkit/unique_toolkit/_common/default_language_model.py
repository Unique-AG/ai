import warnings

from unique_toolkit.language_model.infos import LanguageModelName

warnings.warn(
    "unique_toolkit._common.default_language_model is deprecated. "
    "Import DEFAULT_GPT_4o from unique_toolkit.language_model instead.",
    DeprecationWarning,
    stacklevel=2,
)

DEFAULT_GPT_4o = LanguageModelName.AZURE_GPT_4o_2024_1120
