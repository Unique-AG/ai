"""Chat command: inspect a chat's metadata (id, title, projectScopeId, ...).

Used by the SI ``share-artifact`` skill to decide whether the current
source chat is already anchored to a Project Scope so the skill can
elicit reuse / expand / fork in the multi-artifact case.
"""

from __future__ import annotations

import unique_sdk
from unique_sdk.cli.state import ShellState


def _kv(label: str, value: str | None) -> str:
    return f"{label:<18}{value if value is not None else '-'}"


def cmd_chat_info(state: ShellState, chat_id: str) -> str:
    """Fetch ``GET /chats/{chat_id}`` and render it as a key/value block."""
    try:
        info = unique_sdk.Chat.get_info(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            chat_id=chat_id,
        )
    except (ValueError, unique_sdk.APIError) as e:
        return f"chat info: {e}"

    lines = [
        _kv("id", info.get("id")),
        _kv("title", info.get("title")),
        _kv("assistantId", info.get("assistantId")),
        _kv("projectScopeId", info.get("projectScopeId")),
        _kv("userId", info.get("userId")),
        _kv("companyId", info.get("companyId")),
        _kv("createdAt", info.get("createdAt")),
        _kv("updatedAt", info.get("updatedAt")),
    ]
    return "\n".join(lines)
