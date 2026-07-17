"""Shared deprecation messaging for graduated streaming import paths."""

from __future__ import annotations

import warnings

STREAMING_DEPRECATED_REMOVAL_DATE = "2026-10-17"


def warn_streaming_deprecated_import(*, old_path: str, new_path: str) -> None:
    """Emit a ``DeprecationWarning`` for a moved streaming import path."""
    warnings.warn(
        f"Importing from {old_path!r} is deprecated. "
        f"Use {new_path!r} instead. "
        f"This import path will be removed on {STREAMING_DEPRECATED_REMOVAL_DATE}.",
        DeprecationWarning,
        stacklevel=2,
    )
