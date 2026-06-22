"""Shared path-joining helpers for knowledge-base commands."""

from __future__ import annotations


def join_path_segments(left: str, right: str) -> str:
    """Join two path segments with a single ``/`` separator.

    Strips surrounding whitespace from both sides and collapses the boundary so
    there is exactly one separator between them. A leading slash on ``left`` is
    preserved -- including when ``left`` is the bare root ``/`` -- so absolute
    KB folder paths in ``kb sync`` keep their leading slash. An empty ``left``
    yields just ``right`` so a relative subdirectory join (``kb download``)
    never gains a spurious leading slash.
    """
    rooted = left.strip().startswith("/")
    left = left.strip().rstrip("/")
    right = right.strip().lstrip("/")
    if right == "":
        return left
    if left == "":
        return f"/{right}" if rooted else right
    return f"{left}/{right}"
