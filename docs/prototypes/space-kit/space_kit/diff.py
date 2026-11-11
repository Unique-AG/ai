"""A flat, comparable view of a space: config, settings, fields and MCP."""

import json

from space_kit.base import (
    JsonObject,
    JsonValue,
    KitModel,
    as_list,
    text_or_empty,
)
from space_kit.paths import flatten
from space_kit.payload import COPIED_FIELDS, module_configuration

SECTION_CONFIG = "config"
SECTION_SETTINGS = "settings"
SECTION_SPACE = "space"
SECTION_MCP = "mcp"
VALUE_CHARS = 100
VIEW_FIELDS = (
    *(f for f in COPIED_FIELDS if f != "settings"),
    "name",
    "fallbackModule",
)


class DiffRow(KitModel):
    section: str
    path: str
    left: JsonValue
    right: JsonValue
    left_present: bool = True
    right_present: bool = True


def _mcp_view(*, space: JsonObject) -> dict[str, JsonValue]:
    view: dict[str, JsonValue] = {}
    attachments = as_list(
        value=space.get("assistantMcpServers"), what="assistantMcpServers"
    )
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        name = text_or_empty(value=attachment.get("name"))
        enabled = attachment.get("isEnabled") is True
        tools: list[JsonValue] = [
            text_or_empty(value=tool.get("name"))
            for tool in as_list(value=attachment.get("tools"), what="tools")
            if isinstance(tool, dict) and tool.get("isEnabled") is True
        ]
        view[name] = sorted(tools, key=str) if enabled else "disabled"
    return view


def space_view(*, space: JsonObject) -> dict[str, dict[str, JsonValue]]:
    return {
        SECTION_CONFIG: flatten(data=module_configuration(space=space)),
        SECTION_SETTINGS: flatten(data=space.get("settings") or {}),
        SECTION_SPACE: {key: space.get(key) for key in VIEW_FIELDS if key in space},
        SECTION_MCP: _mcp_view(space=space),
    }


def diff_spaces(*, left: JsonObject, right: JsonObject) -> list[DiffRow]:
    left_view = space_view(space=left)
    right_view = space_view(space=right)
    rows: list[DiffRow] = []
    for section, left_values in left_view.items():
        right_values = right_view[section]
        for path in sorted(left_values.keys() | right_values.keys()):
            in_left = path in left_values
            in_right = path in right_values
            if in_left and in_right and left_values[path] == right_values[path]:
                continue
            rows.append(
                DiffRow(
                    section=section,
                    path=path,
                    left=left_values.get(path),
                    right=right_values.get(path),
                    left_present=in_left,
                    right_present=in_right,
                )
            )
    return rows


def short(*, value: JsonValue, present: bool = True) -> str:
    if not present:
        return "(absent)"
    text = value if isinstance(value, str) else json.dumps(value)
    text = text.replace("\n", "\\n")
    if len(text) > VALUE_CHARS:
        return text[: VALUE_CHARS - 1] + "…"
    return text


def render_rows(*, rows: list[DiffRow]) -> list[str]:
    if not rows:
        return ["no differences"]
    return [
        f"[{row.section}] {row.path}: "
        f"{short(value=row.left, present=row.left_present)} -> "
        f"{short(value=row.right, present=row.right_present)}"
        for row in rows
    ]
