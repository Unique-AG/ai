"""Shared path-joining helpers for knowledge-base commands."""

from __future__ import annotations


def join_path_segments(left: str, right: str) -> str:
    """Join two path segments with a single ``/`` separator.

    Strips surrounding whitespace from both sides and collapses the boundary so
    there is exactly one separator between them. A leading slash on ``left``
    (used for absolute KB folder paths in ``kb sync``) is preserved, while an
    empty side is dropped so a relative subdirectory join (``kb download``)
    never gains a spurious leading slash.
    """
    left = left.strip().rstrip("/")
    right = right.strip().lstrip("/")
    if left == "":
        return right
    if right == "":
        return left
    return f"{left}/{right}"
