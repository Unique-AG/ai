"""Folder-path comparisons shared by the CLI commands."""

from __future__ import annotations

import os

import unique_sdk


def same_folder_path(left: str, right: str) -> bool:
    """True when two folder paths name the same location.

    A missing leading slash and a trailing slash do not make two paths differ.
    """

    def norm(value: str) -> str:
        text = value.strip()
        if text and not text.startswith("/"):
            text = f"/{text}"
        return os.path.normpath(text.rstrip("/")) or "/"

    return norm(left) == norm(right)


def canonical_folder_path(user_id: str, company_id: str, scope_id: str) -> str:
    """Return the stored path for *scope_id*.

    Raises:
        ValueError: The folder has no path.
        unique_sdk.UniqueError: The path lookup failed.
    """
    actual = (
        unique_sdk.Folder.get_folder_path(
            user_id=user_id,
            company_id=company_id,
            scope_id=scope_id,
        ).get("folderPath")
        or ""
    )
    if not actual:
        raise ValueError(f"folder {scope_id} has no path")
    return actual
