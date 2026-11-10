"""Byte-exact JSON sizing and truncation. Sizes are those of ``json_bytes``, except numbers,
which count as Postgres jsonb prints them: the relay reads payloads back with ``json.loads``."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any, Final

from pydantic import JsonValue

# Bytes taken by the quotes and brackets around a value.
_QUOTE_BYTES: Final = 2
_CONTAINER_BRACKET_BYTES: Final = 2
_NULL_BYTES: Final = 4
# Lower than Node's 500: this walk recurses in Python, whose default limit is 1000 frames.
MAX_JSON_DEPTH: Final = 200


def _string_bytes(value: str) -> int:
    # A lone surrogate counts 3 bytes, the size of the U+FFFD that replaces it before insert.
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8", "surrogatepass"))


def _null_non_finite(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _null_non_finite(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_null_non_finite(item) for item in value]
    return value


def json_bytes(value: Any) -> bytes:
    """Serialize compact UTF-8 JSON, writing NaN and Infinity as ``null``.

    Float text can differ from ``JSON.stringify`` by a byte (``1e-07`` vs ``1e-7``), which
    only matters within bytes of a size cap.
    """
    try:
        text = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        )
    except ValueError:
        text = json.dumps(
            _null_non_finite(value),
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    return text.encode("utf-8")


def _number_bytes(value: int | float) -> int:
    if isinstance(value, float) and not math.isfinite(value):
        return _NULL_BYTES
    text = json.dumps(value)
    # Postgres jsonb prints numbers without an exponent, so the stored size is that of the digits.
    return len(format(Decimal(text), "f")) if "e" in text else len(text)


def _scalar_bytes(value: Any) -> int:
    if value is None:
        return _NULL_BYTES
    if isinstance(value, bool):
        return 4 if value else 5
    return _number_bytes(value)


def json_byte_length(value: Any) -> int:
    """Size of the serialised text itself: a float with an exponent counts its short form."""
    return len(json_bytes(value))


def json_byte_length_if_within_limit(
    value: object, max_bytes: float, depth: int = 0
) -> int | None:
    """UTF-8 size of ``json_bytes(value)`` with numbers counted as jsonb prints them (a float
    like ``1e21`` is 22, not 5), or ``None`` once it exceeds ``max_bytes`` (aborts early)."""
    if max_bytes < 0 or depth > MAX_JSON_DEPTH:
        return None
    if value is None or isinstance(value, (bool, int, float)):
        size = _scalar_bytes(value)
    elif isinstance(value, str):
        # Every character costs at least one byte, so a long string can fail without a scan.
        if len(value) + _QUOTE_BYTES > max_bytes:
            return None
        size = _string_bytes(value)
    elif isinstance(value, (list, tuple)):
        return _estimate_array(value, max_bytes, depth)
    elif isinstance(value, dict):
        return _estimate_object(value, max_bytes, depth)
    else:
        raise TypeError(f"Not JSON serializable: {type(value).__name__}")
    return size if size <= max_bytes else None


def _estimate_array(
    value: list[Any] | tuple[Any, ...], max_bytes: float, depth: int
) -> int | None:
    if _CONTAINER_BRACKET_BYTES > max_bytes:
        return None
    size = _CONTAINER_BRACKET_BYTES
    for index, item in enumerate(value):
        separator = 1 if index > 0 else 0
        item_bytes = json_byte_length_if_within_limit(
            item, max_bytes - size - separator, depth + 1
        )
        if item_bytes is None:
            return None
        size += separator + item_bytes
    return size


def _estimate_object(value: dict[str, Any], max_bytes: float, depth: int) -> int | None:
    if _CONTAINER_BRACKET_BYTES > max_bytes:
        return None
    size = _CONTAINER_BRACKET_BYTES
    for index, (key, field) in enumerate(value.items()):
        separator = 1 if index > 0 else 0
        key_bytes = _string_bytes(key)
        remaining = max_bytes - size - separator - key_bytes - 1
        field_bytes = json_byte_length_if_within_limit(field, remaining, depth + 1)
        if field_bytes is None:
            return None
        size += separator + key_bytes + 1 + field_bytes
    return size


def _truncate_string(value: str, max_bytes: float) -> tuple[str, int]:
    """Longest prefix whose JSON size fits ``max_bytes`` (``""`` when even that does not)."""
    low, high = 0, min(len(value), max(int(max_bytes), 0))
    while low < high:
        middle = (low + high + 1) // 2
        if json_byte_length_if_within_limit(value[:middle], max_bytes) is None:
            high = middle - 1
        else:
            low = middle
    return value[:low], _string_bytes(value[:low])


def _shrink(value: object, max_bytes: float, depth: int = 0) -> tuple[Any, int]:
    if depth > MAX_JSON_DEPTH:
        return None, _NULL_BYTES
    if not isinstance(value, (str, list, tuple, dict)):
        return value, _scalar_bytes(value)
    whole = json_byte_length_if_within_limit(value, max_bytes, depth)
    if whole is not None:
        return value, whole
    if isinstance(value, str):
        return _truncate_string(value, max_bytes)
    if isinstance(value, dict):
        return _truncate_object(value, max_bytes, depth)
    return _truncate_array(value, max_bytes, depth)


def _truncate_array(
    value: list[Any] | tuple[Any, ...], max_bytes: float, depth: int
) -> tuple[list[Any], int]:
    """Keeps the leading items that fit, shrinks the boundary item, drops the rest."""
    kept: list[Any] = []
    size = _CONTAINER_BRACKET_BYTES
    for item in value:
        separator = 1 if kept else 0
        item_bytes = json_byte_length_if_within_limit(
            item, max_bytes - size - separator, depth + 1
        )
        if item_bytes is not None:
            kept.append(item)
            size += separator + item_bytes
            continue
        budget = max_bytes - size - separator
        if budget > 0:
            shrunk, shrunk_bytes = _shrink(item, budget, depth + 1)
            if size + separator + shrunk_bytes <= max_bytes:
                kept.append(shrunk)
                size += separator + shrunk_bytes
        break
    return kept, size


def _truncate_object(
    value: dict[str, Any], max_bytes: float, depth: int
) -> tuple[dict[str, Any], int]:
    """Shrinks or drops the largest fields first until the object fits."""
    fields = []
    for key, field in value.items():
        estimated = json_byte_length_if_within_limit(field, max_bytes, depth + 1)
        fields.append(
            (
                key,
                field,
                _string_bytes(key),
                max_bytes + 1 if estimated is None else estimated,
            )
        )

    size = _CONTAINER_BRACKET_BYTES + sum(
        key_bytes + 1 + field_bytes for _, _, key_bytes, field_bytes in fields
    )
    size += max(len(fields) - 1, 0)
    remaining_keys = len(fields)
    shrunk_fields: dict[str, Any] = {}
    dropped: set[str] = set()

    for key, field, key_bytes, field_bytes in sorted(fields, key=lambda f: -f[3]):
        if size <= max_bytes:
            break
        removed_comma = 1 if remaining_keys > 1 else 0
        remaining_keys -= 1
        size -= key_bytes + 1 + field_bytes + removed_comma
        key_overhead = key_bytes + 1 + (1 if remaining_keys > 0 else 0)
        budget = max_bytes - size - key_overhead
        if budget > 0:
            shrunk, shrunk_bytes = _shrink(field, budget, depth + 1)
            if size + key_overhead + shrunk_bytes <= max_bytes:
                shrunk_fields[key] = shrunk
                size += key_overhead + shrunk_bytes
                remaining_keys += 1
                continue
        dropped.add(key)

    result = {
        key: shrunk_fields.get(key, field)
        for key, field in value.items()
        if key not in dropped
    }
    return result, size


def cap_depth(value: object, depth: int = 0) -> tuple[Any, bool]:
    """Replaces every container nested at ``MAX_JSON_DEPTH`` or deeper with ``None``, which
    keeps the result inside the sizing walk's depth limit. Also says whether it cut anything."""
    if not isinstance(value, (list, tuple, dict)):
        return value, False
    if depth >= MAX_JSON_DEPTH:
        return None, True
    if isinstance(value, dict):
        capped = {key: cap_depth(item, depth + 1) for key, item in value.items()}
        return (
            {key: item for key, (item, _) in capped.items()},
            any(cut for _, cut in capped.values()),
        )
    capped_items = [cap_depth(item, depth + 1) for item in value]
    return [item for item, _ in capped_items], any(cut for _, cut in capped_items)


def truncate_json_value_to_bytes(value: object, max_bytes: float) -> JsonValue:
    """Shrinks ``value`` so its compact JSON fits ``max_bytes`` (best effort below 2 bytes):
    strings are cut, arrays keep leading items, objects shrink or drop their largest fields."""
    return _shrink(value, max(max_bytes, 0))[0]


def truncate_to_utf16_length(value: str, max_length: int) -> str:
    """Cuts ``value`` to at most ``max_length`` UTF-16 code units, never inside a surrogate pair."""
    units = 0
    for index, char in enumerate(value):
        units += 2 if char > "￿" else 1
        if units > max_length:
            return value[:index]
    return value
