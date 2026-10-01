from __future__ import annotations

import json
from collections import defaultdict
from enum import Enum
from typing import Any

from unique_search_proxy_client.web.helm.generator.introspect import (
    HelmFieldSpec,
    block_level_fields,
    group_fields_by_section,
    iter_helm_fields,
)
from unique_search_proxy_client.web.helm.registry import HelmSettingsGroup


def _field_property(field: HelmFieldSpec) -> dict[str, Any]:
    prop: dict[str, Any] = {
        "description": f"Maps to env var {field.env_var}.",
    }
    if field.container:
        # Overridable list[str] → JSON array of strings (see _section_properties).
        prop["type"] = "array"
        prop["items"] = {"type": "string"}
    elif field.schema_ref:
        prop["$ref"] = field.schema_ref
    elif field.plain_type == "string":
        prop["type"] = "string"
        if field.format_uri:
            prop["format"] = "uri"
    elif field.plain_type == "number":
        prop["type"] = "number"
    else:
        prop["type"] = "string"
    return prop


def _section_properties(fields: tuple[HelmFieldSpec, ...]) -> dict[str, Any]:
    # Plain (documentation-only) list fields are excluded; a list is exposed in
    # the schema only when explicitly marked overridable.
    return {
        field.helm_name: _field_property(field)
        for field in fields
        if not field.container or field.overridable
    }


def _section_schema(fields: tuple[HelmFieldSpec, ...]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": _section_properties(fields),
    }


def _required_when_enabled_allof(
    fields: tuple[HelmFieldSpec, ...],
    *,
    enabled_const: bool,
) -> list[dict[str, Any]]:
    required_by_section: dict[str, list[str]] = defaultdict(list)
    for field in fields:
        if field.required_when_enabled and not field.container:
            required_by_section[field.section].append(field.helm_name)

    if not required_by_section:
        return []

    section_requirements: dict[str, Any] = {}
    for section, required_names in required_by_section.items():
        section_requirements[section] = {"required": required_names}

    return [
        {
            "if": {
                "properties": {"enabled": {"const": enabled_const}},
                "required": ["enabled"],
            },
            "then": {
                "required": list(required_by_section),
                "properties": section_requirements,
            },
        }
    ]


def _block_level_property(field: HelmFieldSpec) -> dict[str, Any]:
    default = field.default
    if isinstance(default, bool):
        prop: dict[str, Any] = {"type": "boolean"}
    elif isinstance(default, int):
        prop = {"type": "integer"}
    elif isinstance(default, float):
        prop = {"type": "number"}
    else:
        prop = {"type": "string"}

    if isinstance(default, (str, int, float, bool)):
        prop["default"] = default
    if isinstance(default, Enum):
        prop["enum"] = [member.value for member in type(default)]
    prop["description"] = f"Maps to env var {field.env_var}."
    return prop


def _group_schema(group: HelmSettingsGroup) -> dict[str, Any]:
    fields = iter_helm_fields(group.model, env_prefix=group.env_prefix)
    properties = {
        field.helm_name: _block_level_property(field)
        for field in block_level_fields(fields)
    }

    if group.gated:
        properties["enabled"] = {"type": "boolean", "default": False}

    for section_name, section_fields in group_fields_by_section(fields):
        properties[section_name] = _section_schema(section_fields)

    block: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "description": (
            f"{group.title} configuration. Generated from "
            f"{group.model.__name__} ({group.env_prefix}* env vars)."
        ),
        "properties": properties,
    }
    if group.gated:
        all_of = _required_when_enabled_allof(fields, enabled_const=True)
        if all_of:
            block["allOf"] = all_of
    return block


def build_additional_schema(groups: tuple[HelmSettingsGroup, ...]) -> dict[str, Any]:
    properties = {
        group.helm_key: _group_schema(group)
        for group in groups
        if group.helm_key is not None
    }
    return {
        "$schema": "https://json-schema.org/draft-07/schema#",
        "properties": properties,
    }


def render_additional_schema(groups: tuple[HelmSettingsGroup, ...]) -> str:
    return json.dumps(build_additional_schema(groups), indent=2) + "\n"
