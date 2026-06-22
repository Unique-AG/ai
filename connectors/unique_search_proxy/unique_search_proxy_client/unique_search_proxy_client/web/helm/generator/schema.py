from __future__ import annotations

import json
from collections import defaultdict
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
    if field.schema_ref:
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
    return {
        field.helm_name: _field_property(field)
        for field in fields
        if not field.container
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


def _provider_schema(group: HelmSettingsGroup) -> dict[str, Any]:
    fields = iter_helm_fields(group.model, env_prefix=group.env_prefix)
    properties: dict[str, Any] = {
        "enabled": {"type": "boolean", "default": False},
    }
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
    all_of = _required_when_enabled_allof(fields, enabled_const=True)
    if all_of:
        block["allOf"] = all_of
    return block


def _url_safety_schema(group: HelmSettingsGroup) -> dict[str, Any]:
    fields = iter_helm_fields(group.model, env_prefix=group.env_prefix)
    properties: dict[str, Any] = {}
    for block_field in block_level_fields(fields):
        default = block_field.default
        enabled_default = default if isinstance(default, bool) else True
        properties["enabled"] = {"type": "boolean", "default": enabled_default}

    for section_name, section_fields in group_fields_by_section(fields):
        properties[section_name] = _section_schema(section_fields)

    return {
        "type": "object",
        "additionalProperties": False,
        "description": (
            f"{group.title} configuration. Generated from "
            f"{group.model.__name__} ({group.env_prefix}* env vars)."
        ),
        "properties": properties,
    }


def _group_schema(group: HelmSettingsGroup) -> dict[str, Any]:
    if group.kind == "urlSafety":
        return _url_safety_schema(group)
    return _provider_schema(group)


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
