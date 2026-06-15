"""Navigation commands: cd, pwd, ls."""

from __future__ import annotations

from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_ls
from unique_sdk.cli.state import ShellState, _collect_filter_targets


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

        # A non-root target must lie inside the per-message scope: without
        # this, `ls <path>` would enumerate out-of-scope folders/files that
        # read/cite correctly deny. See UN-21780.
        if (
            scope_id is not None
            and state.workspace_metadata_filter is not None
            and not state.folder_allowed_by_metadata_filter(scope_id)
        ):
            return (
                f"ls: permission denied: target is outside your task scope "
                f"({state.scope_denial_hint()})."
            )

        # At root with a per-message KB scope (e.g. an Agentic Table column's
        # scope_rules), show only the in-scope folders and explicitly-scoped
        # documents so the agent explores within the boundary rather than the
        # full company tree or the broader static scope. See UN-21780.
        if scope_id is None and state.workspace_metadata_filter is not None:
            folder_ids, content_ids = _collect_filter_targets(
                state.workspace_metadata_filter
            )
            scoped_folders: list[Any] = []
            for sid in folder_ids:
                try:
                    scoped_folders.append(
                        unique_sdk.Folder.get_info(
                            user_id=state.config.user_id,
                            company_id=state.config.company_id,
                            scopeId=sid,
                        )
                    )
                except unique_sdk.APIError:
                    pass
            scoped_files: list[Any] = []
            for cid in content_ids:
                try:
                    info = unique_sdk.Content.get_info(
                        user_id=state.config.user_id,
                        company_id=state.config.company_id,
                        contentId=cid,
                    )
                    items = info.get("contentInfo", [])
                    if items:
                        scoped_files.append(items[0])
                except unique_sdk.APIError:
                    pass
            output = format_ls(scoped_folders, scoped_files)
            summary = (
                f"\n{len(scoped_folders)} folder(s), {len(scoped_files)} "
                "file(s) in task scope"
            )
            return output + summary

        # When at root with a workspace restriction, show only the allowed scope
        # folders — the agent must not see the full company folder tree.
        if scope_id is None and state.workspace_scope_ids:
            folders: list[Any] = []
            for ws_id in state.workspace_scope_ids:
                try:
                    info = unique_sdk.Folder.get_info(
                        user_id=state.config.user_id,
                        company_id=state.config.company_id,
                        scopeId=ws_id,
                    )
                    folders.append(info)
                except unique_sdk.APIError:
                    pass
            output = format_ls(folders, [])
            summary = f"\n{len(folders)} folder(s), 0 file(s)"
            return output + summary

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

        # With a per-message filter, listing inside an allowed folder must not
        # reveal files the filter excludes (e.g. a combined folder + contentId
        # allowlist): read/cite would deny them, so ls must hide them too.
        # Folder-only filters keep every file (each passes the folderIdPath
        # leaf); the verdict is cached per content id. See UN-21780.
        if state.workspace_metadata_filter is not None:
            files = [
                f for f in files if state.is_content_within_workspace(f.get("id", ""))
            ]
            total_files = len(files)

        output = format_ls(folders, files)
        summary = f"\n{total_folders} folder(s), {total_files} file(s)"
        return output + summary

    except (ValueError, unique_sdk.APIError) as e:
        return f"ls: {e}"
