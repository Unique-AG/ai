import logging
import os

from unique_toolkit.language_model.infos import LanguageModelName

_LOGGER = logging.getLogger(__name__)
_ENV_VAR = "DEFAULT_LANGUAGE_MODEL"
DEFAULT_GPT_4o = LanguageModelName.AZURE_GPT_4o_2024_1120
DEFAULT_GPT_51 = LanguageModelName.AZURE_GPT_51_2025_1113
_LANGUAGE_MODELS_BY_VALUE = {model.value: model for model in LanguageModelName}


def resolve_default_language_model() -> LanguageModelName:
    """Resolve language model name from env var with safe fallback."""
    configured_default = os.getenv(_ENV_VAR)
    if not configured_default:
        return DEFAULT_GPT_51

    # Accept enum values (e.g. "litellm:openai-gpt-5") and member names
    # (e.g. "LITELLM_OPENAI_GPT_5").
    resolved_by_value = _LANGUAGE_MODELS_BY_VALUE.get(configured_default)
    if resolved_by_value is not None:
        return resolved_by_value

    resolved_by_name = LanguageModelName.__members__.get(configured_default)
    if resolved_by_name is not None:
        return resolved_by_name

    _LOGGER.warning(
        "Invalid %s=%r. Falling back to %s.",
        _ENV_VAR,
        configured_default,
        DEFAULT_GPT_51.value,
    )
    return DEFAULT_GPT_51


DEFAULT_LANGUAGE_MODEL = resolve_default_language_model()
