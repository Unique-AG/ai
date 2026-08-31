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

Chat IDs resolve the same way, with one twist: a client spawned during a
chatless preboot carries a synthetic ``chat_preboot*`` placeholder in its
frozen environment. The placeholder never names a real chat (the platform
rejects it), so it is treated as absent at every precedence level and the
turn-identity file supplies the adopted chat's real ID.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

TURN_IDENTITY_ENV_VAR = "UNIQUE_TURN_IDENTITY_FILE"
MESSAGE_ID_ENV_VAR = "UNIQUE_MESSAGE_ID"
CHAT_ID_ENV_VAR = "UNIQUE_CHAT_ID"

# Synthetic chat-id prefix used by the sandbox runner for clients spawned
# before their chat exists (chatless preboot). Adoption re-keys the client
# to the real chat, but the spawn env keeps the placeholder forever.
PREBOOT_CHAT_ID_PREFIX = "chat_preboot"


class TurnIdentityError(ValueError):
    """Raised when the turn-identity file is configured but unusable."""


@dataclass(frozen=True)
class TurnIdentity:
    """Parsed contents of the per-turn identity file.

    The runner writes a richer JSON object (chat/user/company/assistant IDs,
    turn counter), but the CLI only consumes the values that go stale in a
    persistent process environment: ``message_id`` (every turn) and
    ``chat_id`` (adopted chatless-preboot clients). Extra keys are ignored;
    parse a field here only once the CLI actually relies on it.
    """

    message_id: str
    chat_id: str | None = None


def read_turn_identity(
    path: str | Path | None = None,
) -> TurnIdentity | None:
    """Load and validate the turn-identity JSON file.

    When *path* is ``None``, reads ``$UNIQUE_TURN_IDENTITY_FILE``. Returns
    ``None`` when neither is set. Raises ``TurnIdentityError`` if the env
    var / path is set but the file cannot be read or does not contain a
    non-empty ``message_id`` string.
    """
    raw_path = str(path) if path is not None else os.environ.get(TURN_IDENTITY_ENV_VAR)
    if not raw_path:
        return None

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

    chat_id = payload.get("chat_id")
    parsed_chat_id = (
        chat_id.strip() if isinstance(chat_id, str) and chat_id.strip() else None
    )
    return TurnIdentity(message_id=message_id.strip(), chat_id=parsed_chat_id)


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
    if identity is not None:
        return identity.message_id

    env_id = os.environ.get(MESSAGE_ID_ENV_VAR)
    if env_id is not None and env_id.strip():
        return env_id.strip()
    return None


def _usable_chat_id(value: str | None) -> str | None:
    """A non-empty chat id that is not a preboot placeholder, else None."""
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped or stripped.startswith(PREBOOT_CHAT_ID_PREFIX):
        return None
    return stripped


def resolve_chat_id(explicit: str | None = None) -> str | None:
    """Resolve the chat ID for a chat-bound CLI operation.

    Same precedence as :func:`resolve_message_id` (explicit flag, then the
    turn-identity file, then ``$UNIQUE_CHAT_ID``), except a ``chat_preboot*``
    placeholder is skipped at every level — agents pass
    ``--chat-id "$UNIQUE_CHAT_ID"`` from an environment that may have been
    frozen before their chat existed. Returns ``None`` when no source yields
    a real chat id (chat-optional callers then omit the id). Raises
    ``TurnIdentityError`` when the turn-identity file is configured but
    unusable.
    """
    explicit_id = _usable_chat_id(explicit)
    if explicit_id is not None:
        return explicit_id

    identity = read_turn_identity()
    if identity is not None:
        file_id = _usable_chat_id(identity.chat_id)
        if file_id is not None:
            return file_id

    return _usable_chat_id(os.environ.get(CHAT_ID_ENV_VAR))
