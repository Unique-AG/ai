"""Redact customer-derived strings before they are written to a log line.

Filenames keep their extension (plus an optional content id). Prompts, answers,
and tool arguments keep a length. Skill names, scope ids, chat ids, and other
platform identifiers are left as they are.

``get_cid_safe_logger`` only stamps a record with ``CID_SAFE_MARKER``. It does
not remove anything from the message. A host that installs the sandbox
default-deny filter lets stamped records through and drops or replaces the
rest. Until that filter is installed, the stamp has no effect: call
``redact_filename`` (or the other helpers) at the log site.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable, Mapping, MutableMapping
from pathlib import Path, PurePosixPath
from typing import Any, override

# The sandbox filter reads this extra. Do not rename it.
CID_SAFE_MARKER = "unique_cid_safe"

_REDACTED_STEM = "<redacted>"


class CidSafeLoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Stamp reviewed records so a host CID gate can keep the message."""

    @override
    def process(
        self,
        msg: object,
        kwargs: MutableMapping[str, object],
    ) -> tuple[object, MutableMapping[str, object]]:
        extra = dict(self.extra or {})
        call_extra = kwargs.get("extra")
        if isinstance(call_extra, Mapping):
            extra.update(
                (key, value)
                for key, value in call_extra.items()
                if isinstance(key, str)
            )
        extra[CID_SAFE_MARKER] = True
        kwargs["extra"] = extra
        return msg, kwargs


def get_cid_safe_logger(logger: logging.Logger) -> CidSafeLoggerAdapter:
    """Return an adapter that stamps records with ``CID_SAFE_MARKER``.

    Only use it for messages that are already redacted: filenames via
    :func:`redact_filename`, counts, and exception type names. Do not pass raw
    exception text; it can carry a signed URL.
    """
    return CidSafeLoggerAdapter(logger, {})


def redact_filename(
    filename: str | os.PathLike[str] | None,
    *,
    content_id: str | None = None,
) -> str:
    """Return ``<redacted>.<ext>`` (or ``<redacted>.<ext> (id=<cid>)``).

    The extension chain, including compounds like ``.tar.gz``, is preserved.
    """
    if filename is None:
        base = _REDACTED_STEM
    else:
        base = _redact_single_filename(str(filename))

    if content_id:
        return f"{base} (id={content_id})"
    return base


def redact_path(path: str | os.PathLike[str] | None) -> str:
    """Redact the leaf of *path* and keep the parent chain."""
    if path is None or str(path) == "":
        return _REDACTED_STEM
    parsed = Path(str(path))
    safe_name = _redact_single_filename(parsed.name)
    parent = parsed.parent
    if str(parent) in ("", "."):
        return safe_name
    return str(parent / safe_name)


def redact_filenames(
    filenames: Iterable[str | os.PathLike[str]] | None,
) -> list[str]:
    if filenames is None:
        return []
    return [redact_filename(filename) for filename in filenames]


def redact_uploaded_files(
    uploaded: Mapping[str, str] | None,
) -> list[str]:
    """Render ``{filename: content_id}`` as ``["<redacted>.ext (id=cid)", ...]``."""
    if not uploaded:
        return []
    return [redact_filename(name, content_id=cid) for name, cid in uploaded.items()]


def redact_text(
    text: str | None,
    *,
    label: str = "text",
) -> str:
    """Return a length-only marker (``<redacted {label} N chars>``)."""
    if text is None:
        return f"<redacted {label} none>"
    if text == "":
        return f"<redacted {label} empty>"
    return f"<redacted {label} {len(text)} chars>"


def redact_args(args: Any) -> str:
    """Collapse a tool-call payload to its key set and total size.

    Keys stay so it is visible which parameters were set. Values do not.
    """
    if args is None:
        return "<no args>"
    if isinstance(args, dict):
        if not args:
            return "<empty args>"
        keys = ", ".join(sorted(map(str, args.keys())))
        try:
            length = len(repr(args))
        except Exception:
            length = -1
        if length >= 0:
            return f"{{{keys}}} ({length} chars)"
        return f"{{{keys}}}"
    if isinstance(args, str):
        return redact_text(args, label="scalar")
    return f"<redacted {type(args).__name__} args>"


def redact_body_preview(body: bytes | str | None) -> str:
    """Length-only marker for an HTTP request or response body."""
    if body is None:
        return "<redacted body none>"
    try:
        size = len(body)
    except TypeError:
        return "<redacted body>"
    return f"<redacted body {size} bytes>"


_COMPOUND_SUFFIXES: tuple[str, ...] = (
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tar.zst",
)

# Strip log-hostile characters from a captured extension so a hostile filename
# cannot smuggle shell metacharacters into a log line.
_SAFE_EXT_RE = re.compile(r"[^A-Za-z0-9._-]")


def _redact_single_filename(name: str) -> str:
    cleaned = name.strip().strip("/").strip("\\")
    if not cleaned:
        return _REDACTED_STEM
    leaf = PurePosixPath(cleaned).name or cleaned
    lower = leaf.lower()
    for compound in _COMPOUND_SUFFIXES:
        if lower.endswith(compound):
            return f"{_REDACTED_STEM}{_sanitize_ext(compound)}"
    suffix = PurePosixPath(leaf).suffix
    if not suffix:
        return _REDACTED_STEM
    return f"{_REDACTED_STEM}{_sanitize_ext(suffix)}"


def _sanitize_ext(ext: str) -> str:
    return _SAFE_EXT_RE.sub("", ext)


__all__ = [
    "CID_SAFE_MARKER",
    "get_cid_safe_logger",
    "redact_args",
    "redact_body_preview",
    "redact_filename",
    "redact_filenames",
    "redact_path",
    "redact_text",
    "redact_uploaded_files",
]
