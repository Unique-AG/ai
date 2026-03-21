"""Navigation commands: cd, pwd, ls."""

from __future__ import annotations

from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_ls
from unique_sdk.cli.state import ShellState


def cmd_pwd(state: ShellState) -> str:
    return state.cwd


def cmd_cd(state: ShellState, target: str) -> str:
    """Change directory and return status message."""
    try:
        new_path = state.cd(target)
        return new_path
    except (ValueError, unique_sdk.APIError) as e:
        return f"cd: {e}"


def cmd_ls(state: ShellState, target: str | None = None) -> str:
    """List folders and files at the given (or current) path."""
    try:
        if target is not None:
            _, scope_id = state.resolve_path(target)
        else:
            scope_id = state.scope_id

        folder_params: dict[str, Any] = {}
        content_params: dict[str, Any] = {}
        if scope_id:
            folder_params["parentId"] = scope_id
            content_params["parentId"] = scope_id

        folder_result = unique_sdk.Folder.get_infos(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **folder_params,
        )
        folders = folder_result.get("folderInfos", [])

        content_result = unique_sdk.Content.get_infos(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **content_params,
        )
        files = content_result.get("contentInfos", [])

        total_folders = folder_result.get("totalCount", len(folders))
        total_files = content_result.get("totalCount", len(files))

        output = format_ls(folders, files)
        summary = f"\n{total_folders} folder(s), {total_files} file(s)"
        return output + summary

    except (ValueError, unique_sdk.APIError) as e:
        return f"ls: {e}"
