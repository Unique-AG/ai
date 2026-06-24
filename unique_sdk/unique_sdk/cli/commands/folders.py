"""Folder commands: mkdir, rmdir, rename (mv for folders)."""

from __future__ import annotations

import os

import unique_sdk
from unique_sdk.cli.formatting import format_folder_info
from unique_sdk.cli.state import ShellState


def _resolve_folder_scope_id(state: ShellState, target: str) -> str | None:
    """Resolve a folder target (scope id or path) to its scope id, or None.

    Used to gate folder mutations against a per-message ``metaDataFilter``.
    Returns None when the target can't be resolved so callers fail closed.
    """
    if target.startswith("scope_"):
        return target
    try:
        _, scope_id = state.resolve_path(target)
    except Exception:
        return None
    return scope_id


def _metadata_filter_denies_folder(state: ShellState, scope_id: str | None) -> bool:
    """True if a per-message filter is active and *scope_id* is outside it.

    ``is_folder_target_within_workspace`` only enforces the static
    ``scopeIds`` (and treats "no scopeIds" as unrestricted), so folder
    mutations slip past a per-message ``metaDataFilter`` that read/cite/ls/
    search honour. Gate them against the filter too. Fails closed when the
    target can't be resolved. See UN-21780.
    """
    if state.workspace_metadata_filter is None:
        return False
    if not scope_id:
        return True
    return not state.folder_allowed_by_metadata_filter(scope_id)


def cmd_mkdir(state: ShellState, name: str) -> str:
    """Create a new folder under the current directory."""
    # A per-message metaDataFilter *replaces* the static scopeIds, so the
    # static-scope check must not over-deny an in-filter destination; the
    # normalized path is gated against the filter below. See UN-21780.
    if (
        state.workspace_metadata_filter is None
        and not state.is_folder_target_within_workspace(name)
    ):
        return "mkdir: permission denied (outside workspace scope)"
    # Resolve the destination (collapsing any `..`) and gate the *path*, not
    # just the current scope id: `mkdir ../../Other/X` would otherwise pass a
    # cwd-only check and create structure outside the per-message task scope.
    full_path = os.path.normpath(f"{state.cwd.rstrip('/')}/{name}")
    if not state.folder_path_allowed_by_metadata_filter(full_path):
        return (
            "mkdir: permission denied: destination is outside your task scope "
            f"({state.scope_denial_hint()})."
        )
    try:
        result = unique_sdk.Folder.create_paths(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            paths=[full_path],
        )
        created = result.get("createdFolders", [])
        if created:
            last = created[-1]
            return f"Created: {full_path} ({last['id']})"
        return f"Created: {full_path}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"mkdir: {e}"


def cmd_rmdir(state: ShellState, target: str, recursive: bool = False) -> str:
    """Delete a folder by path or scope ID."""
    # An active per-message filter replaces the static scopeIds, so skip the
    # static-scope check (it would over-deny an in-filter target); the filter
    # gate below is authoritative. See UN-21780.
    if (
        state.workspace_metadata_filter is None
        and not state.is_folder_target_within_workspace(target)
    ):
        return "rmdir: permission denied (outside workspace scope)"
    if _metadata_filter_denies_folder(state, _resolve_folder_scope_id(state, target)):
        return (
            "rmdir: permission denied: target is outside your task scope "
            f"({state.scope_denial_hint()})."
        )
    try:
        if target.startswith("scope_"):
            unique_sdk.Folder.delete(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                scopeId=target,
                recursive=recursive,
            )
            return f"Deleted folder: {target}"
        else:
            if not target.startswith("/"):
                target = f"{state.cwd.rstrip('/')}/{target}"
            unique_sdk.Folder.delete(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                folderPath=target,
                recursive=recursive,
            )
            return f"Deleted folder: {target}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"rmdir: {e}"


def cmd_mvdir(state: ShellState, old_name: str, new_name: str) -> str:
    """Rename a folder."""
    # An active per-message filter replaces the static scopeIds, so skip the
    # static-scope check (it would over-deny an in-filter target); the filter
    # gate below is authoritative. See UN-21780.
    if (
        state.workspace_metadata_filter is None
        and not state.is_folder_target_within_workspace(old_name)
    ):
        return "mvdir: permission denied (outside workspace scope)"
    if _metadata_filter_denies_folder(state, _resolve_folder_scope_id(state, old_name)):
        return (
            "mvdir: permission denied: target is outside your task scope "
            f"({state.scope_denial_hint()})."
        )
    try:
        if old_name.startswith("scope_"):
            result = unique_sdk.Folder.update(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                scopeId=old_name,
                name=new_name,
            )
        else:
            if not old_name.startswith("/"):
                old_name = f"{state.cwd.rstrip('/')}/{old_name}"
            result = unique_sdk.Folder.update(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                folderPath=old_name,
                name=new_name,
            )
        return f"Renamed folder -> {result.get('name', new_name)}\n{format_folder_info(result)}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"mvdir: {e}"
