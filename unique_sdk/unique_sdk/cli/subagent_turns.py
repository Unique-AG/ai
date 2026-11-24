"""Record of the subagent turns that ``unique-cli subagent`` has running.

A caller that kills the command outright (SIGKILL) gives it no chance to stop
the subagent turn. The record lets the caller's host find that turn afterwards
and stop it. Each running turn is one file, so parallel commands never write
to the same file and a killed command leaves its own record behind.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import TypedDict

TURNS_DIRNAME = ".unique-subagent-turns"

_log = logging.getLogger(__name__)
_RECORD_SUFFIX = ".json"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class SubagentTurn(TypedDict):
    chatId: str
    messageId: str


def turns_dir_for(config_path: Path) -> Path:
    """Return the record directory that belongs to a subagent config file."""
    return config_path.parent / TURNS_DIRNAME


def record_turn_started(turns_dir: Path, *, chat_id: str, message_id: str) -> None:
    """Record a running turn. A failure is logged and never raised."""
    record_path = _record_path(turns_dir, message_id=message_id)
    if record_path is None:
        return
    turn: SubagentTurn = {"chatId": chat_id, "messageId": message_id}
    partial_path = record_path.with_suffix(".partial")
    try:
        turns_dir.mkdir(parents=True, exist_ok=True)
        partial_path.write_text(json.dumps(turn), encoding="utf-8")
        # The rename is atomic, so a reader never sees a half-written record.
        os.replace(partial_path, record_path)
    except OSError as exc:
        _log.warning("Could not record the subagent turn: %s", type(exc).__name__)


def record_turn_ended(turns_dir: Path, *, message_id: str) -> None:
    """Remove the record of a turn that no longer needs a stop."""
    record_path = _record_path(turns_dir, message_id=message_id)
    if record_path is None:
        return
    try:
        record_path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("Could not clear the subagent turn: %s", type(exc).__name__)


def read_open_turns(turns_dir: Path) -> list[SubagentTurn]:
    """Return every recorded turn. Unreadable records are skipped."""
    try:
        record_paths = sorted(turns_dir.glob(f"*{_RECORD_SUFFIX}"))
    except OSError:
        return []
    turns: list[SubagentTurn] = []
    for record_path in record_paths:
        try:
            raw = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        chat_id = raw.get("chatId")
        message_id = raw.get("messageId")
        if isinstance(chat_id, str) and isinstance(message_id, str):
            turns.append({"chatId": chat_id, "messageId": message_id})
    return turns


def _record_path(turns_dir: Path, *, message_id: str) -> Path | None:
    # The id becomes a file name, so it MUST NOT carry a path separator.
    if not _SAFE_ID.fullmatch(message_id):
        return None
    return turns_dir / f"{message_id}{_RECORD_SUFFIX}"
