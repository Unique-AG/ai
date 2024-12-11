from typing import Any, Dict

from unique_toolkit.language_model import LanguageModel, LanguageModelName


def validate_and_init_language_model(value: LanguageModelName | LanguageModel | str):
    if isinstance(value, LanguageModel):
        return value

    return LanguageModel(value)


def validate_required_parameters(params: Dict[str, Any]) -> None:
    """
    Validates that all required parameters are present and not None.

    Args:
        params (Dict[str, Any]): Dictionary of parameter names and their values

    Raises:
        ValueError: If any required parameters are missing or None
    """
    missing_params = [k for k, v in params.items() if v is None]
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
