from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelProvider,
)

# TODO @klcd: Inform on deprecation of str as input
LMI = Annotated[
    LanguageModelInfo,
    BeforeValidator(
        lambda v: validate_and_init_language_model_info(v),
        json_schema_input_type=str | LanguageModelName | LanguageModelInfo,
    ),
    PlainSerializer(
        lambda v: serialize_lmi(v),
        when_used="json",
        return_type=str | LanguageModelInfo,
    ),
]


def serialize_lmi(model: LanguageModelInfo) -> str | LanguageModelInfo:
    if model.provider == LanguageModelProvider.CUSTOM:
        return model

    return model.name


def validate_and_init_language_model_info(
    v: str | LanguageModelName | LanguageModelInfo,
) -> LanguageModelInfo:
    """Validate and initialize a LanguageModelInfo object.

    Args:
        v: The input value to validate and initialize.

    Returns:
        LanguageModelInfo: The validated and initialized LanguageModelInfo object.

    """
    if isinstance(v, LanguageModelName):
        return LanguageModelInfo.from_name(v)
    if isinstance(v, str):
        if v in [name.value for name in LanguageModelName]:
            return LanguageModelInfo.from_name(LanguageModelName(v))

        return LanguageModelInfo(
            name=v,
            version="custom",
            provider=LanguageModelProvider.CUSTOM,
        )

    return v
