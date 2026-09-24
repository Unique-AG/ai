"""Row shaping for Unique platform iframe hosts.

The platform resolves ``data-unique-field="identity.name"`` as ``item["identity.name"]``,
not nested ``item.identity.name``. Live-local hosts traverse nested JSON via
``readPath()``. Tool responses therefore carry both shapes: nested domain objects
plus dotted-path mirror keys and a few precomputed attribute values the platform
cannot interpolate from ``{field}`` templates.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def flatten_dotted_paths(value: Any, *, prefix: str = "") -> dict[str, Any]:
    """Recursively mirror nested dict/list values as top-level dotted keys."""
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(child, dict):
                out.update(flatten_dotted_paths(child, prefix=path))
            elif isinstance(child, list):
                for index, item in enumerate(child):
                    item_path = f"{path}.{index}"
                    if isinstance(item, dict):
                        out.update(flatten_dotted_paths(item, prefix=item_path))
                    else:
                        out[item_path] = item
            else:
                out[path] = child
    return out


def due_date_bucket(value: Any, *, today: date | None = None) -> str:
    """Map a due date to ``urgent`` / ``scheduled`` / ``none`` for portfolio filters."""
    if value is None or value == "":
        return "none"
    text = str(value).strip()[:10]
    try:
        due = date.fromisoformat(text)
    except ValueError:
        return "none"
    ref = today or date.today()
    return "urgent" if due <= ref else "scheduled"


def enrich_binding_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return a row dict with nested data, dotted mirrors, and platform attr helpers."""
    flat = flatten_dotted_paths(row)
    merged = {**row, **flat}

    client_id = row.get("id")
    if client_id is not None:
        merged["client_href"] = f"#client-{client_id}"
        merged["client_dom_id"] = f"client-{client_id}"

    risk_level = flat.get("compliance.risk_level")
    if risk_level is not None:
        merged["compliance.risk_level_tooltip"] = f"{risk_level} risk"

    merged["case_action.due_bucket"] = due_date_bucket(flat.get("case_action.due_date"))

    for key, value in flat.items():
        if key.endswith(".pct") and value is not None:
            merged[f"{key}_bar_style"] = f"width:{value}%"

    return merged
