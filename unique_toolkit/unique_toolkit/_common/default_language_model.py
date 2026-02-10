import warnings

from unique_toolkit.language_model.default_language_model import (
    DEFAULT_GPT_4o as DEFAULT_GPT_4o, DEFAULT_LANGUAGE_MODEL as DEFAULT_LANGUAGE_MODEL,
)

warnings.warn(
    "unique_toolkit._common.default_language_model is deprecated. "
    "Import DEFAULT_GPT_4o from unique_toolkit.language_model instead.",
    DeprecationWarning,
    stacklevel=2,
)

