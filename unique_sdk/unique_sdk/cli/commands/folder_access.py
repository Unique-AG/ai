"""Folder access command: inspect the current ScopeAccess list of a scope.

Wraps :func:`unique_sdk.Folder.get_info`, which already returns the
``scopeAccess`` array. Used by the SI ``share-artifact`` skill to detect
whether new recipients are inside or outside an existing project before
deciding between ``expand`` and ``fork``.
"""

from __future__ import annotations

from typing import Any, cast

import unique_sdk
from unique_sdk.cli.state import ShellState


def cmd_folder_access(state: ShellState, target: str) -> str:
    """Show the ScopeAccess list for ``target`` (path or ``scope_...`` id)."""
    try:
        if target.startswith("scope_"):
            info_raw = unique_sdk.Folder.get_info(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                scopeId=target,
            )
        else:
            if not target.startswith("/"):
                target = f"{state.cwd.rstrip('/')}/{target}"
            info_raw = unique_sdk.Folder.get_info(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                folderPath=target,
            )
        info = cast("dict[str, Any]", cast("object", info_raw))
    except (ValueError, unique_sdk.APIError) as e:
        return f"folder access: {e}"

    accesses_raw = info.get("scopeAccess") or []
    accesses = cast("list[dict[str, Any]]", accesses_raw)
    if not accesses:
        return f"(no scope access entries on {info.get('id') or target})"

    rows: list[list[str]] = []
    for a in accesses:
        rows.append(
            [
                str(a.get("entityType", "?")),
                str(a.get("entityId", "?")),
                str(a.get("type", "?")),
            ]
        )
    header = ["TYPE", "ENTITY_ID", "ACCESS"]
    widths = [len(h) for h in header]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    out = [
        "  ".join(h.ljust(widths[i]) for i, h in enumerate(header)),
        "  ".join("-" * w for w in widths),
    ]
    for row in rows:
        out.append("  ".join(row[i].ljust(widths[i]) for i in range(len(header))))
    return "\n".join(out)
