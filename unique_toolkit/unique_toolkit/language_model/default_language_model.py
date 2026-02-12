import logging
import os

from unique_toolkit.language_model.infos import LanguageModelName

_LOGGER = logging.getLogger(__name__)

_DEFAULT_LANGUAGE_MODEL_ENV_VAR = "DEFAULT_LANGUAGE_MODEL"
DEFAULT_GPT_4o = LanguageModelName.AZURE_GPT_4o_2024_1120


def resolve_default_language_model(
    env_var: str = _DEFAULT_LANGUAGE_MODEL_ENV_VAR,
    fallback: LanguageModelName = DEFAULT_GPT_4o,
) -> LanguageModelName:
    """Resolve language model name from env var with safe fallback."""
    configured_default = os.getenv(env_var)
    if not configured_default:
        return fallback

    try:
        return LanguageModelName(configured_default)
    except ValueError:
        # Also accept enum member names, e.g. "AZURE_GPT_4o_2024_1120".
        try:
            return LanguageModelName[configured_default]
        except KeyError:
            _LOGGER.warning(
                "Invalid %s=%r. Falling back to %s.",
                env_var,
                configured_default,
                fallback.value,
            )
            return fallback

DEFAULT_LANGUAGE_MODEL: LanguageModelName = resolve_default_language_model()