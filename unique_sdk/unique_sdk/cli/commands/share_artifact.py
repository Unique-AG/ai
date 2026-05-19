"""Share-artifact command: POST /share-artifact.

Wraps :func:`unique_sdk.ShareArtifact.create`. The SI agent's
``share-artifact`` skill is the canonical caller: it resolves the
artifact, elicits recipients and the quick message, asks for
expand-vs-fork when required, then invokes this command.
"""

from __future__ import annotations

import json

import unique_sdk
from unique_sdk.cli.state import ShellState


def _split_csv(values: tuple[str, ...]) -> list[str]:
    """Flatten repeated ``--user-id a,b -u c`` into ``[a, b, c]``."""
    out: list[str] = []
    for value in values:
        if not value:
            continue
        for piece in value.split(","):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


def cmd_share_artifact(
    state: ShellState,
    content_id: str,
    *,
    source_chat_id: str,
    project_name: str,
    user_ids: tuple[str, ...] = (),
    group_ids: tuple[str, ...] = (),
    expand_project: bool | None = None,
    message: str | None = None,
    output_json: bool = False,
) -> str:
    """Invoke ``POST /share-artifact`` and pretty-print the result."""
    resolved_users = _split_csv(user_ids)
    resolved_groups = _split_csv(group_ids)
    if not resolved_users and not resolved_groups:
        return (
            "share-artifact: provide at least one recipient via --user-id and/or "
            "--group-id (comma-separated or repeated)."
        )

    try:
        result = unique_sdk.ShareArtifact.create(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            sourceChatId=source_chat_id,
            contentId=content_id,
            recipientUserIds=resolved_users,
            recipientGroupIds=resolved_groups,
            projectName=project_name,
            expandProject=expand_project,
            quickMessage=message,
        )
    except (ValueError, unique_sdk.APIError) as e:
        return f"share-artifact: {e}"

    if output_json:
        return json.dumps(result, indent=2, default=str)

    lines: list[str] = []
    lines.append(f"projectAction   {result.get('projectAction', '-')}")
    lines.append(f"projectScopeId  {result.get('projectScopeId', '-')}")
    lines.append(f"projectPath     {result.get('projectPath', '-')}")
    notifications = result.get("notifications") or []
    lines.append(f"notifications   {len(notifications)} delivered")
    for n in notifications:
        via = n.get("viaGroupIds") or []
        via_str = f" (via groups {', '.join(via)})" if via else ""
        lines.append(
            f"  - {n.get('userId', '?')}  notification={n.get('notificationId') or '<flag-off>'}{via_str}"
        )
    skipped = result.get("skippedRecipients") or []
    if skipped:
        lines.append(f"skipped         {len(skipped)}")
        for s in skipped:
            lines.append(f"  - {s.get('userId', '?')}  reason={s.get('reason', '?')}")
    return "\n".join(lines)
