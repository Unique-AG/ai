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

The file may also carry an ``elicitation_target``. A sub-agent turn runs in a
hidden chat, so its runner names the parent chat and message there. ``elicit
ask`` and ``elicit create`` then create the elicitation on that target, whatever
``--chat-id`` and ``--message-id`` say.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

TURN_IDENTITY_ENV_VAR = "UNIQUE_TURN_IDENTITY_FILE"
MESSAGE_ID_ENV_VAR = "UNIQUE_MESSAGE_ID"
CHAT_ID_ENV_VAR = "UNIQUE_CHAT_ID"
ELICITATION_TARGET_KEY = "elicitation_target"

# Synthetic chat-id prefix used by the sandbox runner for clients spawned
# before their chat exists (chatless preboot). Adoption re-keys the client
# to the real chat, but the spawn env keeps the placeholder forever.
PREBOOT_CHAT_ID_PREFIX = "chat_preboot"


class TurnIdentityError(ValueError):
    """Raised when the turn-identity file is configured but unusable."""


@dataclass(frozen=True)
class ElicitationTarget:
    """Where this turn's elicitations go when the user is in another chat.

    A sub-agent turn runs in a hidden chat. Its runner names the parent chat
    and message here, so the user sees the question. ``header`` is put in
    front of the question, and ``metadata`` is added to the elicitation.
    """

    chat_id: str
    message_id: str
    header: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def with_header(self, message: str) -> str:
        if not self.header:
            return message
        return f"{self.header}\n\n{message}"


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
    elicitation_target: ElicitationTarget | None = None


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
    return TurnIdentity(
        message_id=message_id.strip(),
        chat_id=parsed_chat_id,
        elicitation_target=_parse_elicitation_target(
            payload.get(ELICITATION_TARGET_KEY), raw_path=raw_path
        ),
    )


def _parse_elicitation_target(
    raw: object, *, raw_path: str
) -> ElicitationTarget | None:
    """A malformed target is an error: the question would land where nobody sees it."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TurnIdentityError(
            f"turn-identity file {raw_path!r}: {ELICITATION_TARGET_KEY!r} "
            "must be a JSON object"
        )
    ids: dict[str, str] = {}
    for key in ("chat_id", "message_id"):
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise TurnIdentityError(
                f"turn-identity file {raw_path!r}: {ELICITATION_TARGET_KEY!r} "
                f"is missing a non-empty {key!r} string"
            )
        ids[key] = value.strip()
    header = raw.get("header")
    metadata = raw.get("metadata")
    return ElicitationTarget(
        chat_id=ids["chat_id"],
        message_id=ids["message_id"],
        header=header.strip() if isinstance(header, str) else "",
        metadata={
            key: value
            for key, value in (metadata if isinstance(metadata, dict) else {}).items()
            if isinstance(key, str) and isinstance(value, str)
        },
    )


def resolve_elicitation_target() -> ElicitationTarget | None:
    """The elicitation target of the current turn, or None for the turn's own chat.

    Raises ``TurnIdentityError`` when the turn-identity file is configured but
    unusable.
    """
    identity = read_turn_identity()
    if identity is None:
        return None
    return identity.elicitation_target


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
