import logging
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer, ValidationInfo
from pydantic.fields import FieldInfo

from unique_toolkit.language_model.enum_narrowing import (
    build_language_model_enum_from_names,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
    LanguageModelProvider,
)

logger = logging.getLogger(__name__)

# TODO @klcd: Inform on deprecation of str as input
LMI = Annotated[
    LanguageModelInfo,
    BeforeValidator(
        lambda v: validate_and_init_language_model_info(v),
        json_schema_input_type=LanguageModelName
        | Annotated[
            str,
            Field(
                title="Language Model String",
            ),
        ]
        | LanguageModelInfo,
    ),
    PlainSerializer(
        lambda v: serialize_lmi(v),
        when_used="json",
        return_type=str | LanguageModelInfo,
    ),
]


def _build_restricted_lmi_validator(
    allowed_model_names: set[str],
) -> Callable[[Any], LanguageModelInfo]:
    def _validate(v: Any) -> LanguageModelInfo:
        info = validate_and_init_language_model_info(v)
        if str(info.name) not in allowed_model_names:
            raise ValueError(
                f"Language model {info.name!r} is not available for this tenant."
            )
        return info

    return _validate


def build_lmi_annotation(available_models: list[str]) -> Any:
    """
    Return an Annotated LMI type whose json_schema_input_type is restricted
    to `available_models`. Drop-in replacement for LMI in model_json_schema()
    calls that need a tenant-scoped schema.
    """
    if not available_models:
        return LMI

    narrowed_enum = build_language_model_enum_from_names(available_models)
    allowed_model_names = {member.value for member in narrowed_enum}
    return Annotated[
        LanguageModelInfo,
        BeforeValidator(
            _build_restricted_lmi_validator(allowed_model_names),
            json_schema_input_type=narrowed_enum,
        ),
        PlainSerializer(
            serialize_lmi,
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
    if isinstance(v, LanguageModelName | str):
        return LanguageModelInfo.from_name(v)

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
