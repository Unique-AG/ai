"""User and group lookup commands.

Thin wrappers over :class:`unique_sdk.User` and :class:`unique_sdk.Group`,
shaped for the SI ``share-artifact`` skill: search by name fragment,
inspect a group's membership, list known groups so the skill can resolve
recipient inputs to ids before calling :class:`unique_sdk.ShareArtifact`.
"""

from __future__ import annotations

import unique_sdk
from unique_sdk.cli.state import ShellState


def _format_user_row(u: unique_sdk.User.User) -> list[str]:
    return [
        u.get("id", "?"),
        u.get("displayName") or u.get("userName") or "-",
        u.get("email") or "-",
        "active" if u.get("active") else "inactive",
    ]


def _format_table(header: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "(no rows)"
    widths = [len(h) for h in header]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
    out: list[str] = []
    out.append("  ".join(h.ljust(widths[i]) for i, h in enumerate(header)))
    out.append("  ".join("-" * w for w in widths))
    for row in rows:
        out.append(
            "  ".join(
                (row[i] if i < len(row) else "").ljust(widths[i])
                for i in range(len(widths))
            )
        )
    return "\n".join(out)


def cmd_users_search(
    state: ShellState,
    query: str | None,
    *,
    email: str | None = None,
    limit: int = 50,
) -> str:
    """Search users by display name (or email) and return id + name + email.

    ``query`` matches partial display name (case-insensitive on the server).
    Pass ``--email`` to filter by email instead. ``--limit`` caps results.
    """
    try:
        users = unique_sdk.User.get_users(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            take=limit,
            displayName=query if query else None,
            email=email,
        )
    except (ValueError, unique_sdk.APIError) as e:
        return f"users search: {e}"

    rows = [_format_user_row(u) for u in users.get("users", [])]
    if not rows:
        return "(no users matched)"
    return _format_table(["ID", "NAME", "EMAIL", "STATUS"], rows)


def cmd_groups_list(state: ShellState, *, query: str | None = None, limit: int = 100) -> str:
    """List groups visible to the caller (optionally filtered by ``--name``)."""
    try:
        result = unique_sdk.Group.get_groups(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            take=limit,
            name=query if query else None,
        )
    except (ValueError, unique_sdk.APIError) as e:
        return f"groups list: {e}"

    rows: list[list[str]] = []
    for g in result.get("groups", []):
        rows.append([g.get("id", "?"), g.get("name") or "-", g.get("externalId") or "-"])
    if not rows:
        return "(no groups)"
    return _format_table(["ID", "NAME", "EXTERNAL_ID"], rows)


def cmd_group_members(state: ShellState, group_id: str) -> str:
    """List the users of a group: ``id  name``."""
    try:
        result = unique_sdk.Group.get_group_members(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            group_id=group_id,
        )
    except (ValueError, unique_sdk.APIError) as e:
        return f"group members: {e}"

    rows: list[list[str]] = []
    for m in result.get("members", []):
        rows.append([m.get("id", "?"), m.get("name") or "-"])
    if not rows:
        return f"(group {group_id} has no members)"
    return _format_table(["ID", "NAME"], rows)
