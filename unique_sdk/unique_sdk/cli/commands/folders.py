"""Folder commands: mkdir, rmdir, rename (mv for folders)."""

from __future__ import annotations

import unique_sdk

from unique_sdk.cli.formatting import format_folder_info
from unique_sdk.cli.state import ShellState


def cmd_mkdir(state: ShellState, name: str) -> str:
    """Create a new folder under the current directory."""
    try:
        full_path = f"{state.cwd.rstrip('/')}/{name}"
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
