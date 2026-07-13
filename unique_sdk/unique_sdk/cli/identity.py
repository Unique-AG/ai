"""Resolve the current turn's assistant message identity.

Persistent agent subprocesses freeze their OS environment at spawn time, so
``UNIQUE_MESSAGE_ID`` can be stale on later turns. The parent runner writes a
per-turn identity file and exposes its path via ``UNIQUE_TURN_IDENTITY_FILE``
(stable across turns). Fresh ``unique-cli`` invocations then read the current
message ID from that file.

Resolution precedence for message IDs:

1. Explicit ``--message-id`` / ``-m`` flag value
2. Turn-identity file pointed to by ``$UNIQUE_TURN_IDENTITY_FILE``
3. ``$UNIQUE_MESSAGE_ID`` environment variable (one-shot / external callers)

When ``UNIQUE_TURN_IDENTITY_FILE`` is set but the file is missing or malformed,
resolution fails loudly — silent fallback to a stale env value is forbidden.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

TURN_IDENTITY_ENV_VAR = "UNIQUE_TURN_IDENTITY_FILE"
MESSAGE_ID_ENV_VAR = "UNIQUE_MESSAGE_ID"
CHAT_ID_ENV_VAR = "UNIQUE_CHAT_ID"


class TurnIdentityError(ValueError):
    """Raised when the turn-identity file is configured but unusable."""


def read_turn_identity(
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate the turn-identity JSON file.

    When *path* is ``None``, reads ``$UNIQUE_TURN_IDENTITY_FILE``. Raises
    ``TurnIdentityError`` if the env var / path is set but the file cannot be
    read or does not contain a non-empty ``message_id`` string.
    """
    raw_path = str(path) if path is not None else os.environ.get(TURN_IDENTITY_ENV_VAR)
    if not raw_path:
        return {}

    identity_path = Path(raw_path)
    if not identity_path.is_file():
        raise TurnIdentityError(
            f"{TURN_IDENTITY_ENV_VAR} is set to {raw_path!r} but the file "
            "is missing; refusing to fall back to a stale message id"
        )
    if identity_path.is_symlink():
        raise TurnIdentityError(
            f"refusing to read turn-identity file {raw_path!r}: path is a symlink"
        )

    try:
        payload = json.loads(identity_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TurnIdentityError(
            f"failed to read turn-identity file {raw_path!r}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise TurnIdentityError(
            f"turn-identity file {raw_path!r} must contain a JSON object"
        )

    message_id = payload.get("message_id")
    if not isinstance(message_id, str) or not message_id.strip():
        raise TurnIdentityError(
            f"turn-identity file {raw_path!r} is missing a non-empty "
            "'message_id' string"
        )
    return payload


def resolve_message_id(explicit: str | None = None) -> str | None:
    """Resolve the assistant message ID for a message-bound CLI operation.

    Returns ``None`` when no source yields a value (callers may then mint a
    placeholder message, as elicit does for visible prompts without a chat
    context). Raises ``TurnIdentityError`` when the turn-identity file is
    configured but unusable.
    """
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()

    identity = read_turn_identity()
    if identity:
        message_id = identity.get("message_id")
        if isinstance(message_id, str) and message_id.strip():
            return message_id.strip()

    env_id = os.environ.get(MESSAGE_ID_ENV_VAR)
    if env_id is not None and env_id.strip():
        return env_id.strip()
    return None


def resolve_chat_id(explicit: str | None = None) -> str | None:
    """Resolve chat ID with the same file-then-env precedence as message ID.

    Explicit flag wins. The turn-identity file is consulted next (and fails
    loudly when configured but unusable). Falls back to ``$UNIQUE_CHAT_ID``.
    """
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()

    identity = read_turn_identity()
    if identity:
        chat_id = identity.get("chat_id")
        if isinstance(chat_id, str) and chat_id.strip():
            return chat_id.strip()

    env_id = os.environ.get(CHAT_ID_ENV_VAR)
    if env_id is not None and env_id.strip():
        return env_id.strip()
    return None
