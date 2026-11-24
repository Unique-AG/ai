"""Records of running subagent turns, so a host can stop them after the CLI is killed.

One file per turn under ``.unique/subagent-turns/`` in the workspace root.
The agent can write to the workspace, so a record is untrusted: a host MUST
check ``parentChatId`` and ``parentMessageId`` against the parent turn it runs
and the subagent chats it knows before it stops anything.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Literal, TypedDict

TURNS_RELATIVE_DIR = ".unique/subagent-turns"
RECORD_VERSION = 1

_log = logging.getLogger(__name__)
_RECORD_SUFFIX = ".json"
_PARTIAL_SUFFIX = ".partial"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class SubagentTurn(TypedDict):
    version: Literal[1]
    chatId: str
    messageId: str
    parentChatId: str | None
    parentMessageId: str | None


def record_turn_started(
    *,
    turns_dir: Path,
    chat_id: str,
    message_id: str,
    parent_chat_id: str | None,
    parent_message_id: str | None,
) -> None:
    """Record a running turn. A failure is logged and never raised."""
    record_path = _record_path(turns_dir=turns_dir, message_id=message_id)
    if record_path is None:
        return
    turn: SubagentTurn = {
        "version": RECORD_VERSION,
        "chatId": chat_id,
        "messageId": message_id,
        "parentChatId": parent_chat_id,
        "parentMessageId": parent_message_id,
    }
    partial_path = record_path.with_suffix(_PARTIAL_SUFFIX)
    try:
        turns_dir.mkdir(parents=True, exist_ok=True)
        partial_path.write_text(json.dumps(turn), encoding="utf-8")
        # The rename is atomic, so a reader never sees a half-written record.
        os.replace(partial_path, record_path)
    except OSError as exc:
        _log.warning("Could not record the subagent turn: %s", type(exc).__name__)
        try:
            partial_path.unlink(missing_ok=True)
        except OSError:
            pass


def record_turn_ended(*, turns_dir: Path, message_id: str) -> None:
    """Remove the record of a turn that no longer needs a stop."""
    record_path = _record_path(turns_dir=turns_dir, message_id=message_id)
    if record_path is None:
        return
    try:
        record_path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("Could not clear the subagent turn: %s", type(exc).__name__)


def read_open_turns(*, turns_dir: Path) -> list[SubagentTurn]:
    """Return every recorded turn. Unusable records are skipped with a warning."""
    try:
        record_paths = sorted(turns_dir.glob(f"*{_RECORD_SUFFIX}"))
    except OSError:
        return []
    turns: list[SubagentTurn] = []
    for record_path in record_paths:
        try:
            raw: object = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            # ValueError covers both invalid JSON and invalid UTF-8.
            _log.warning(
                "Skipped an unreadable subagent turn record: %s", type(exc).__name__
            )
            continue
        turn = _parse_turn(raw)
        if turn is None:
            _log.warning("Skipped a subagent turn record with an unknown format")
            continue
        turns.append(turn)
    return turns


def _parse_turn(raw: object) -> SubagentTurn | None:
    if not isinstance(raw, dict) or raw.get("version") != RECORD_VERSION:
        return None
    chat_id = raw.get("chatId")
    message_id = raw.get("messageId")
    parent_chat_id = raw.get("parentChatId")
    parent_message_id = raw.get("parentMessageId")
    if not (isinstance(chat_id, str) and isinstance(message_id, str)):
        return None
    if not (_is_optional_str(parent_chat_id) and _is_optional_str(parent_message_id)):
        return None
    return {
        "version": RECORD_VERSION,
        "chatId": chat_id,
        "messageId": message_id,
        "parentChatId": parent_chat_id,
        "parentMessageId": parent_message_id,
    }


def _is_optional_str(value: object) -> bool:
    return value is None or isinstance(value, str)


def _record_path(*, turns_dir: Path, message_id: str) -> Path | None:
    # The id becomes a file name, so it MUST NOT carry a path separator.
    if not _SAFE_ID.fullmatch(message_id):
        _log.warning(
            "Subagent turn not recorded: the message id is not a safe file name"
        )
        return None
    return turns_dir / f"{message_id}{_RECORD_SUFFIX}"
