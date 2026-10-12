"""Navigation commands: cd, pwd, ls."""

from __future__ import annotations

import os
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_ls
from unique_sdk.cli.metadata_filter import _collect_filter_targets
from unique_sdk.cli.state import ShellState


def cmd_pwd(state: ShellState) -> str:
    return state.cwd


def cmd_cd(state: ShellState, target: str) -> str:
    """Change directory and return status message."""
    try:
        new_path = state.cd(target)
        return new_path
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"cd: {e}"


def _same_folder_path(left: str, right: str) -> bool:
    """True when two folder paths name the same location."""

    def norm(value: str) -> str:
        text = value.strip()
        if text and not text.startswith("/"):
            text = f"/{text}"
        return os.path.normpath(text.rstrip("/")) or "/"

    return norm(left) == norm(right)


def _empty_listing_error(
    state: ShellState,
    target: str,
    resolved_path: str,
    scope_id: str,
    total_folders: int,
    total_files: int,
) -> str | None:
    """Distinguish an empty folder from one this call could not list.

    A reported count with no rows, or a scope id whose canonical path is not
    the path that was asked for, is a refusal. A matching path with zero
    counts is a real empty folder.
    """
    if total_folders or total_files:
        return (
            f"ls: cannot list {target}: listing returned no entries "
            f"({total_folders} folder(s), {total_files} file(s) reported)"
        )
    try:
        actual = (
            unique_sdk.Folder.get_folder_path(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                scope_id=scope_id,
            ).get("folderPath")
            or ""
        )
    except (ValueError, unique_sdk.UniqueError):
        return None
    if not actual or not _same_folder_path(actual, resolved_path):
        shown = actual or "(unknown)"
        return (
            f"ls: cannot list {target}: resolved to {shown} instead (not listable here)"
        )
    return None


def _with_unlistable_marker(output: str, unlistable: list[str]) -> str:
    """Append folders that could not be listed, or fail when none could."""
    if not unlistable:
        return output
    if output.startswith("(empty)"):
        return "ls: cannot list " + ", ".join(unlistable) + " (not listable)"
    return output + "\nnot listable: " + ", ".join(unlistable)


def is_ls_error_output(output: str) -> bool:
    """Return True when *output* is a ``cmd_ls`` error.

    Success listings start with a table, ``(empty)``, or a count. Failures
    start with ``ls:`` and must exit non-zero from the one-shot CLI.
    """
    return output.startswith("ls:")


def cmd_ls(state: ShellState, target: str | None = None) -> str:
    """List folders and files at the given (or current) path."""
    try:
        if target is not None:
            resolved_path, scope_id = state.resolve_path(target)
        else:
            resolved_path, scope_id = state.cwd, state.scope_id

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
            _, content_ids = _collect_filter_targets(state.workspace_metadata_filter)
            # Only show folders that are actually browsable: a folder reachable
            # solely as an OR-alternative to a contentId allowlist is not a
            # standalone scope, so listing it would leak inventory. See
            # UN-21780.
            folder_ids = state.navigable_folder_ids()
            scoped_folders: list[Any] = []
            unlistable_folders: list[str] = []
            for sid in folder_ids:
                try:
                    scoped_folders.append(
                        unique_sdk.Folder.get_info(
                            user_id=state.config.user_id,
                            company_id=state.config.company_id,
                            scopeId=sid,
                        )
                    )
                except unique_sdk.UniqueError:
                    unlistable_folders.append(sid)
            scoped_files: list[Any] = []
            for cid in content_ids:
                # A contentId mentioned in the filter is not necessarily in
                # scope on its own: an AND branch (e.g. contentId IN [x] AND
                # folderIdPath A) can exclude it. Verify against the full
                # filter so root ls never shows a title that read/cite and
                # in-folder ls deny. Cached, so no extra API cost. See
                # UN-21780.
                if not state.is_content_within_workspace(cid):
                    continue
                try:
                    info = unique_sdk.Content.get_info(
                        user_id=state.config.user_id,
                        company_id=state.config.company_id,
                        contentId=cid,
                    )
                    items = info.get("contentInfo", [])
                    if items:
                        scoped_files.append(items[0])
                except unique_sdk.UniqueError:
                    pass
            output = format_ls(scoped_folders, scoped_files)
            summary = (
                f"\n{len(scoped_folders)} folder(s), {len(scoped_files)} "
                "file(s) in task scope"
            )
            return _with_unlistable_marker(output + summary, unlistable_folders)

        # When at root with a workspace restriction, show only the allowed scope
        # folders — the agent must not see the full company folder tree.
        if scope_id is None and state.workspace_scope_ids:
            folders: list[Any] = []
            unlistable_folders = []
            for ws_id in state.workspace_scope_ids:
                try:
                    info = unique_sdk.Folder.get_info(
                        user_id=state.config.user_id,
                        company_id=state.config.company_id,
                        scopeId=ws_id,
                    )
                    folders.append(info)
                except unique_sdk.UniqueError:
                    unlistable_folders.append(ws_id)
            output = format_ls(folders, [])
            summary = f"\n{len(folders)} folder(s), 0 file(s)"
            return _with_unlistable_marker(output + summary, unlistable_folders)

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

        if target is not None and scope_id and not folders and not files:
            empty_error = _empty_listing_error(
                state,
                target,
                resolved_path,
                scope_id,
                total_folders,
                total_files,
            )
            if empty_error:
                return empty_error

        # With a per-message filter, listing inside an allowed folder must not
        # reveal files the filter excludes (e.g. a combined folder + contentId
        # allowlist): read/cite would deny them, so ls must hide them too.
        # Folder-only filters keep every file (each passes the folderIdPath
        # leaf); the verdict is cached per content id. See UN-21780.
        if state.workspace_metadata_filter is not None:
            files = [
                f for f in files if state.is_content_within_workspace(f.get("id", ""))
            ]
            # ``files`` is only the current API page, so the in-scope count is
            # per-page, not the folder total. Report it as the shown-in-scope
            # count and keep the API ``totalCount`` as the folder's real size,
            # rather than overwriting total_files with the page length (which
            # would silently undercount paginated folders). See UN-21780.
            output = format_ls(folders, files)
            summary = (
                f"\n{total_folders} folder(s), {len(files)} file(s) in task scope "
                f"(of {total_files} in folder)"
            )
            return output + summary

        output = format_ls(folders, files)
        summary = f"\n{total_folders} folder(s), {total_files} file(s)"
        return output + summary

    except (ValueError, unique_sdk.UniqueError) as e:
        return f"ls: {e}"
