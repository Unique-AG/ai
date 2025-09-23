import logging
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer, ValidationInfo
from pydantic.fields import FieldInfo

from unique_toolkit.language_model import LanguageModelName
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelProvider,
)

logger = logging.getLogger(__name__)

# TODO @klcd: Inform on deprecation of str as input
LMI = Annotated[
    LanguageModelInfo,
    BeforeValidator(
        lambda v: validate_and_init_language_model_info(v),
        json_schema_input_type=LanguageModelName | LanguageModelInfo | Annotated[
            str,
            Field(
                title="Language Model String",
            )
        ],
    ),
    PlainSerializer(
        lambda v: serialize_lmi(v),
        when_used="json",
        return_type=str | LanguageModelInfo,
    ),
]


def get_LMI_default_field(llm_name: LanguageModelName, **kwargs) -> Any:
    return Field(
        default=LanguageModelInfo.from_name(llm_name),
        json_schema_extra={"default": llm_name},
        **kwargs,
    )


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


def ClipInt(*, min_value: int, max_value: int) -> tuple[BeforeValidator, FieldInfo]:
    def _validator(value: Any, info: ValidationInfo) -> Any:
        if not isinstance(value, int):
            value = int(value)

        field_name = info.field_name
        if value < min_value:
            logger.warning(
                "Field %s is below the allowed minimum of %s. It will be set to %s.",
                field_name,
                min_value,
                min_value,
            )
            return min_value

        if value > max_value:
            logger.warning(
                "Field %s is above the allowed maximum of %s. It will be set to %s.",
                field_name,
                max_value,
                max_value,
            )
            return max_value

        return value

    return (BeforeValidator(_validator), Field(ge=min_value, le=max_value))
