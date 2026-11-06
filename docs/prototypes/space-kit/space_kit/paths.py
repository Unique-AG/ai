"""Dotted paths into JSON config, with `list[name]` selectors for tools.

`claude.effort` addresses a key. `tools[WebSearch].isEnabled` addresses the
list item whose `name` is `WebSearch`. Two MCP tools can share a name, so
`tools[search@mcp_abc]` also matches `configuration.mcpServerId`.
"""

import copy
import json
from pathlib import Path

from space_kit.base import JsonObject, JsonValue, KitModel, SpaceKitError

FILE_PREFIX = "@file:"
SERVER_SEPARATOR = "@"


class Segment(KitModel):
    key: str
    selector: str | None = None


class Assignment(KitModel):
    path: str
    value: JsonValue


def parse_path(*, path: str) -> tuple[Segment, ...]:
    segments: list[Segment] = []
    for part in _split_outside_brackets(text=path):
        key, bracket, rest = part.partition("[")
        if not key or (bracket and not rest.endswith("]")):
            msg = f"malformed path {path!r} near {part!r}"
            raise SpaceKitError(msg)
        selector = rest[:-1] if bracket else None
        segments.append(Segment(key=key, selector=selector))
    if not segments:
        msg = "empty path"
        raise SpaceKitError(msg)
    return tuple(segments)


def _split_outside_brackets(*, text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "." and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        depth += {"[": 1, "]": -1}.get(char, 0)
        current.append(char)
    parts.append("".join(current))
    return parts


def _item_server(*, item: JsonObject) -> str:
    inner = item.get("configuration")
    if isinstance(inner, dict):
        server = inner.get("mcpServerId")
        if isinstance(server, str):
            return server
    return ""


def _matches(*, item: JsonValue, selector: str) -> bool:
    if not isinstance(item, dict):
        return False
    name, _, server = selector.partition(SERVER_SEPARATOR)
    if item.get("name") != name:
        return False
    return not server or _item_server(item=item) == server


def _select(*, items: list[JsonValue], selector: str, where: str) -> JsonObject:
    found = [item for item in items if _matches(item=item, selector=selector)]
    if len(found) != 1:
        msg = (
            f"{where}[{selector}] matches {len(found)} items; "
            "use name@mcpServerId when two tools share a name"
        )
        raise SpaceKitError(msg)
    chosen = found[0]
    assert isinstance(chosen, dict)
    return chosen


def _step(*, node: JsonObject, segment: Segment, where: str, create: bool) -> JsonValue:
    if segment.key not in node:
        if not create:
            known = ", ".join(sorted(node)) or "(none)"
            msg = f"{where}.{segment.key} does not exist; known keys: {known}"
            raise SpaceKitError(msg)
        node[segment.key] = [] if segment.selector else {}
    child = node[segment.key]
    if segment.selector is None:
        return child
    if not isinstance(child, list):
        msg = f"{where}.{segment.key} is not a list"
        raise SpaceKitError(msg)
    return _select(
        items=child, selector=segment.selector, where=f"{where}.{segment.key}"
    )


def get_path(*, data: JsonObject, path: str) -> JsonValue:
    node: JsonValue = data
    where = "config"
    for segment in parse_path(path=path):
        if not isinstance(node, dict):
            msg = f"{where} is not an object"
            raise SpaceKitError(msg)
        node = _step(node=node, segment=segment, where=where, create=False)
        where = f"{where}.{segment.key}"
    return node


def set_path(
    *, data: JsonObject, assignment: Assignment, allow_new_keys: bool
) -> JsonObject:
    """A copy of `data` with the value set. Unknown keys are refused
    unless allowed, so a typo cannot add a key the runtime ignores."""
    result = copy.deepcopy(data)
    segments = parse_path(path=assignment.path)
    node: JsonValue = result
    where = "config"
    for segment in segments[:-1]:
        if not isinstance(node, dict):
            msg = f"{where} is not an object"
            raise SpaceKitError(msg)
        node = _step(node=node, segment=segment, where=where, create=allow_new_keys)
        where = f"{where}.{segment.key}"
    last = segments[-1]
    if not isinstance(node, dict) or last.selector is not None:
        msg = f"cannot assign to {assignment.path}: target is not a key"
        raise SpaceKitError(msg)
    if last.key not in node and not allow_new_keys:
        known = ", ".join(sorted(node)) or "(none)"
        msg = (
            f"{where}.{last.key} does not exist (known keys: {known}); "
            "pass --allow-new-keys if this is intended"
        )
        raise SpaceKitError(msg)
    node[last.key] = assignment.value
    return result


def _list_keys(*, items: list[JsonValue]) -> list[str] | None:
    """Selector keys for a list of named objects, or None for a plain list."""
    if not items or not all(
        isinstance(item, dict) and isinstance(item.get("name"), str) for item in items
    ):
        return None
    names = [str(item["name"]) for item in items if isinstance(item, dict)]
    keys: list[str] = []
    for item in items:
        assert isinstance(item, dict)
        name = str(item["name"])
        server = _item_server(item=item)
        unique = names.count(name) == 1
        keys.append(name if unique or not server else f"{name}@{server}")
    return keys


def flatten(*, data: JsonValue, prefix: str = "") -> dict[str, JsonValue]:
    if isinstance(data, dict):
        flat: dict[str, JsonValue] = {}
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            flat.update(flatten(data=value, prefix=path))
        return flat or {prefix: {}}
    if isinstance(data, list):
        keys = _list_keys(items=data)
        if keys is None:
            return {prefix: data}
        flat = {}
        for key, item in zip(keys, data, strict=True):
            flat.update(flatten(data=item, prefix=f"{prefix}[{key}]"))
        return flat
    return {prefix: data}


def parse_value(*, text: str, base_dir: Path) -> JsonValue:
    """JSON when it parses, file content for `@file:<path>`, else text."""
    if text.startswith(FILE_PREFIX):
        path = Path(text.removeprefix(FILE_PREFIX)).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"cannot read {path}: {exc.strerror}"
            raise SpaceKitError(msg) from exc
    try:
        parsed: JsonValue = json.loads(text)
    except json.JSONDecodeError:
        return text
    return parsed


def resolve_value(*, value: JsonValue, base_dir: Path) -> JsonValue:
    if isinstance(value, str) and value.startswith(FILE_PREFIX):
        return parse_value(text=value, base_dir=base_dir)
    return value


def parse_assignment(*, text: str, base_dir: Path) -> Assignment:
    path, separator, raw = text.partition("=")
    if not separator or not path.strip():
        msg = f"expected path=value, got {text!r}"
        raise SpaceKitError(msg)
    return Assignment(path=path.strip(), value=parse_value(text=raw, base_dir=base_dir))
