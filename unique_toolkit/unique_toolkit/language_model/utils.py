import json as j
import logging
import os
import re
from functools import lru_cache

_LOGGER = logging.getLogger(__name__)

# Environment variable name for custom language model infos
LANGUAGE_MODEL_INFOS_ENV_VAR = "LANGUAGE_MODEL_INFOS"


@lru_cache(maxsize=1)
def load_language_model_infos_from_env() -> dict[str, dict]:
    """
    Load custom language model infos from environment variable.

    The environment variable should contain a JSON string with a dict of
    LanguageModelInfo-compatible dictionaries. The key is used for model lookup.

    Example:
        LANGUAGE_MODEL_INFOS='{"AZURE_GPT_4o_CUSTOM": {"name": "AZURE_GPT_4o_2024_1120",
        "provider": "AZURE", "version": "custom", "capabilities": ["function_calling",
        "streaming", "vision"], "token_limits": {"token_limit_input": 3000,
        "token_limit_output": 150}}}'

    Returns:
        A dictionary mapping model keys to their info dictionaries.
    """
    env_value = os.getenv(LANGUAGE_MODEL_INFOS_ENV_VAR)
    if not env_value:
        return {}

    try:
        model_infos_dict = j.loads(env_value)
        if not isinstance(model_infos_dict, dict):
            _LOGGER.error(
                f"{LANGUAGE_MODEL_INFOS_ENV_VAR} must be a JSON dict of model info objects. "
                f"Got {type(model_infos_dict).__name__} instead."
            )
            return {}

        # Validate each entry in the dictionary
        valid_model_infos: dict[str, dict] = {}
        for model_key, model_info in model_infos_dict.items():
            if not isinstance(model_info, dict):
                _LOGGER.warning(
                    f"Skipping invalid model info entry '{model_key}' in {LANGUAGE_MODEL_INFOS_ENV_VAR}: "
                    f"expected dict, got {type(model_info).__name__}"
                )
                continue

            valid_model_infos[model_key] = model_info

        _LOGGER.debug(
            f"Loaded {len(valid_model_infos)} custom language model infos from {LANGUAGE_MODEL_INFOS_ENV_VAR}"
        )
        return valid_model_infos

    except j.JSONDecodeError:
        _LOGGER.error(
            f"Failed to parse {LANGUAGE_MODEL_INFOS_ENV_VAR} as JSON. "
            "The environment variable should contain a valid JSON dict of model info objects.",
            exc_info=True,
        )
        return {}


def convert_string_to_json(string: str):
    """
    Removes any json tags and converts string to json.

    Args:
        string: The string to convert to json.

    Returns:
        dict: The json object.

    Raises:
        ValueError: If the string cannot be converted to json.
    """
    cleaned_result = find_last_json_object(string)
    if not cleaned_result:
        raise ValueError("Could not find a valid json object in the string.")
    try:
        json = j.loads(cleaned_result)
    except j.JSONDecodeError:
        raise ValueError("Could not convert the string to JSON.")
    return json


def find_last_json_object(text: str) -> str | None:
    """
    Finds the last json object in a string.

    Args:
        text: The text to search for the last json object.

    Returns:
        str | None: The last json object as a string or None if no json object was found.
    """

    pattern = r"\{(?:[^{}]|\{[^{}]*\})*\}"
    matches = re.findall(pattern, text)
    if matches:
        return matches[-1]
    else:
        return None


def format_message(user: str, message: str, num_tabs: int = 1) -> str:
    """
    Formats a message from a user by indenting each line with a specified number of tabs.

    Args:
        user (str): The name of the user sending the message.
        message (str): The message content that may include multiple lines.
        num_tabs (int): The number of tabs to use for indenting each line. Default is 1 tab.

    Returns:
        str: A formatted string with user and indented message lines.

    Example:
        >>> format_message("Alice", "Hello\nWorld", 2)
        Alice:
        \t\tHello
        \t\tWorld
    """
    indentation = "\t" * num_tabs
    indented_message = message.replace("\n", "\n" + indentation)
    formatted_message = f"{user}:\n{indentation}{indented_message}"
    return formatted_message
