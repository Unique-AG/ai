"""Shared helpers for the per-turn citation refs manifest under ``.unique/``.

Both ``unique-cli search`` (KB) and ``unique-cli web-search`` (web) append
to a small per-turn JSONL file inside the current workspace's ``.unique``
directory so that the Swappable Intelligence runner can later substitute
``[sourceN]`` / ``[websourceN]`` markers in the LLM answer with footnotes
and reference chips.

The handshake is symmetric across the two callers — the file name, lock
file name, and on-disk layout differ, but the safety + locking +
read/append semantics are identical. This module owns that machinery so
neither caller has to maintain its own copy.

Each caller passes its own ``refs_log_path`` (absolute path) and lock
filename in. Nothing in this module is web- or KB-specific.
"""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

__all__ = [
    "UnsafeRefsLogPathError",
    "_append_turn_refs_manifest_entry",
    "_locked_turn_refs_manifest",
    "_read_turn_refs_manifest",
]


class UnsafeRefsLogPathError(OSError):
    """Raised when the internal refs log path would follow a symlink.

    Callers should treat this as a hard failure for the current command —
    refuse to render results, and surface the error via the caller's
    usual ``<prefix>: <message>`` error string convention.
    """


def _assert_safe_refs_log_path(refs_log_path: Path) -> None:
    """Reject symlinks for the parent dir, the manifest, or any file at
    the same path that is not a regular file.

    This is intentionally strict: the manifest path is a fixed,
    well-known handoff path used by another process (the runner) running
    in the same workspace. Following symlinks here would let a malicious
    workspace redirect writes elsewhere.

    Writer-side counterpart to the reader-side check at
    ``swappable_intelligence.runner.CodingAgentRunner._is_safe_turn_refs_log_path``
    in ``monorepo``. The two run in different processes (this one in the
    agent's bash sandbox, the reader in assistants-core) so they cannot
    share code; keep the rejection policy aligned across the two when
    either is edited.
    """
    refs_log_dir = refs_log_path.parent
    if refs_log_dir.is_symlink() or (
        refs_log_dir.exists() and not refs_log_dir.is_dir()
    ):
        raise UnsafeRefsLogPathError(
            f"refusing unsafe refs log directory: {refs_log_dir}"
        )
    if refs_log_path.is_symlink():
        raise UnsafeRefsLogPathError(f"refusing unsafe refs log file: {refs_log_path}")
    if refs_log_path.exists() and not refs_log_path.is_file():
        raise UnsafeRefsLogPathError(f"refusing unsafe refs log file: {refs_log_path}")


def _read_turn_refs_manifest(refs_log_path: Path) -> list[dict[str, Any]]:
    """Return all valid JSON object lines from the manifest, in order.

    Blank lines and lines that fail to parse as a JSON object are
    silently skipped — this matches the runner's tolerance for malformed
    lines and keeps a stray partial write from breaking the next call.
    """
    _assert_safe_refs_log_path(refs_log_path)
    if not refs_log_path.is_file():
        return []
    try:
        raw_lines = refs_log_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise UnsafeRefsLogPathError(
            f"failed to read refs log: {refs_log_path}"
        ) from exc

    entries: list[dict[str, Any]] = []
    for raw in raw_lines:
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _append_turn_refs_manifest_entry(
    refs_log_path: Path,
    payload: dict[str, Any],
) -> None:
    """Append one JSON object as a single line, creating parents if needed.

    Uses ``O_NOFOLLOW`` and a 0o600 mode so a symlink swap between the
    safety check and the open call still fails closed.
    """
    _assert_safe_refs_log_path(refs_log_path)
    try:
        refs_log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UnsafeRefsLogPathError(
            f"failed to create refs log directory: {refs_log_path.parent}"
        ) from exc
    _assert_safe_refs_log_path(refs_log_path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(refs_log_path, flags, 0o600)
    except OSError as exc:
        raise UnsafeRefsLogPathError(
            f"failed to open refs log safely: {refs_log_path}"
        ) from exc
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, default=str, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise UnsafeRefsLogPathError(
            f"failed to write refs log: {refs_log_path}"
        ) from exc


@contextmanager
def _locked_turn_refs_manifest(
    refs_log_path: Path,
    *,
    lock_filename: str,
) -> Generator[None, None, None]:
    """Hold an ``fcntl.flock`` on a sibling lock file for the duration of
    a read-existing → compute-next-number → append-new sequence.

    The lock file lives in the same ``.unique`` directory as the manifest
    so concurrent ``unique-cli`` invocations from the same workspace
    serialise their appends and never race the source-number counter.
    """
    lock_path = refs_log_path.parent / lock_filename
    _assert_safe_refs_log_path(lock_path)
    try:
        refs_log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UnsafeRefsLogPathError(
            f"failed to create refs log directory: {refs_log_path.parent}"
        ) from exc
    _assert_safe_refs_log_path(lock_path)

    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise UnsafeRefsLogPathError(
            f"failed to open refs lock safely: {lock_path}"
        ) from exc

    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as exc:
        os.close(fd)
        raise UnsafeRefsLogPathError(
            f"failed to lock refs manifest: {lock_path}"
        ) from exc

    try:
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)
