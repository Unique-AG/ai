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

def filter_language_models_in_schema(
    schema: dict[str, Any],
    available_models: list[str] | None,
) -> dict[str, Any]:
    if not available_models:
        return schema

    # Keep order, remove duplicates
    available_values = list(dict.fromkeys(available_models))
    available_set = set(available_values)

    defs = schema.get("$defs", {})
    if not isinstance(defs, dict):
        return schema

    # 1) Filter canonical enum def
    language_model_name_def = defs.get("LanguageModelName")
    if (
        isinstance(language_model_name_def, dict)
        and isinstance(language_model_name_def.get("enum"), list)
    ):
        language_model_name_def["enum"] = [
            value
            for value in language_model_name_def["enum"]
            if value in available_set
        ]

    # 2) Restrict "Language Model String" defs as requested
    for def_schema in defs.values():
        if not isinstance(def_schema, dict):
            continue
        if def_schema.get("title") != "Language Model String":
            continue

        if isinstance(def_schema.get("enum"), list):
            def_schema["enum"] = [
                value for value in def_schema["enum"] if value in available_set
            ]
        else:
            def_schema["enum"] = available_values.copy()

    # 3) Ensure defaults referencing these defs remain valid
    filtered_language_model_values: list[str] = []
    if (
        isinstance(language_model_name_def, dict)
        and isinstance(language_model_name_def.get("enum"), list)
    ):
        filtered_language_model_values = language_model_name_def["enum"]

    replacement_default = (
        filtered_language_model_values[0]
        if filtered_language_model_values
        else (available_values[0] if available_values else None)
    )
    if replacement_default is None:
        return schema

    def _ref_targets_lm_defs(ref: str) -> bool:
        # ref format expected: "#/$defs/<name>"
        prefix = "#/$defs/"
        if not ref.startswith(prefix):
            return False
        def_name = ref[len(prefix) :]
        target = defs.get(def_name)
        if def_name == "LanguageModelName":
            return True
        return isinstance(target, dict) and target.get("title") == "Language Model String"

    def _property_references_language_model(prop_schema: dict[str, Any]) -> bool:
        # direct $ref
        direct_ref = prop_schema.get("$ref")
        if isinstance(direct_ref, str) and _ref_targets_lm_defs(direct_ref):
            return True

        # anyOf refs/inline branches
        any_of = prop_schema.get("anyOf")
        if isinstance(any_of, list):
            for branch in any_of:
                if not isinstance(branch, dict):
                    continue

                ref = branch.get("$ref")
                if isinstance(ref, str) and _ref_targets_lm_defs(ref):
                    return True

                if branch.get("title") == "Language Model String":
                    return True

        return False

    def _fix_defaults_in_properties(properties: dict[str, Any]) -> None:
        for prop_schema in properties.values():
            if not isinstance(prop_schema, dict):
                continue

            current_default = prop_schema.get("default")
            if not isinstance(current_default, str) or current_default in available_set:
                continue

            if _property_references_language_model(prop_schema):
                prop_schema["default"] = replacement_default

    root_properties = schema.get("properties", {})
    if isinstance(root_properties, dict):
        _fix_defaults_in_properties(root_properties)

    # Also validate defaults in schema definitions containing properties,
    # e.g. $defs["ChunkRelevancySortConfig"]["properties"][...]
    for def_schema in defs.values():
        if not isinstance(def_schema, dict):
            continue

        def_properties = def_schema.get("properties")
        if isinstance(def_properties, dict):
            _fix_defaults_in_properties(def_properties)

    return schema