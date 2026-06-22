from __future__ import annotations

import json
from typing import Any

from unique_search_proxy_client.web.helm.generator.introspect import (
    HelmFieldSpec,
    iter_helm_fields,
)
from unique_search_proxy_client.web.helm.registry import HelmSettingsGroup


def _connection_property(field: HelmFieldSpec) -> dict[str, Any]:
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


def _provider_schema(group: HelmSettingsGroup) -> dict[str, Any]:
    fields = iter_helm_fields(group.model, env_prefix=group.env_prefix)
    required_when_enabled = [
        field.helm_name for field in fields if field.required_when_enabled
    ]
    connection_props = {
        field.helm_name: _connection_property(field) for field in fields
    }
    block: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "description": (
            f"{group.title} configuration. Generated from "
            f"{group.model.__name__} ({group.env_prefix}* env vars)."
        ),
        "properties": {
            "enabled": {"type": "boolean", "default": False},
            "connection": {
                "type": "object",
                "additionalProperties": False,
                "properties": connection_props,
            },
        },
    }
    if required_when_enabled:
        block["allOf"] = [
            {
                "if": {
                    "properties": {"enabled": {"const": True}},
                    "required": ["enabled"],
                },
                "then": {
                    "required": ["connection"],
                    "properties": {
                        "connection": {"required": required_when_enabled},
                    },
                },
            }
        ]
    return block


def build_additional_schema(groups: tuple[HelmSettingsGroup, ...]) -> dict[str, Any]:
    properties = {
        group.helm_key: _provider_schema(group)
        for group in groups
        if group.helm_key is not None
    }
    return {
        "$schema": "https://json-schema.org/draft-07/schema#",
        "properties": properties,
    }


def render_additional_schema(groups: tuple[HelmSettingsGroup, ...]) -> str:
    return json.dumps(build_additional_schema(groups), indent=2) + "\n"
