"""Navigation commands: cd, pwd, ls."""

from __future__ import annotations

from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_ls
from unique_sdk.cli.metadata_filter import _collect_filter_targets
from unique_sdk.cli.state import ShellState

# For the root-scoped branches, which list explicit ids and so have no server
# page to inherit. The paginated branch sends no ``take``: page size is the
# server's, and counts come from response lengths, never from a constant.
LS_LOCAL_PAGE_SIZE = 50


def cmd_pwd(state: ShellState) -> str:
    return state.cwd


def cmd_cd(state: ShellState, target: str) -> str:
    """Change directory and return status message."""
    try:
        new_path = state.cd(target)
        return new_path
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"cd: {e}"


def _count(shown: int, total: int, noun: str) -> str:
    """``N noun(s)``, or ``N of M noun(s)`` when the listing was partial."""
    return f"{shown} {noun}(s)" if shown == total else f"{shown} of {total} {noun}(s)"


def _footer(
    skip: int,
    target: str | None,
    command_prefix: str,
    folders: tuple[int, int],
    files: tuple[int, int],
    *,
    summary: str | None = None,
    suffix: str = "",
) -> str:
    """Summary line, plus a truncation notice when a listing was cut short.

    *folders* and *files* are ``(shown, total)`` pairs. *summary* overrides the
    default line for callers whose shown-count differs from the page length.
    """
    kinds = (("folder", folders), ("file", files))
    if summary is None:
        summary = ", ".join(_count(*counts, noun) for noun, counts in kinds)
    summary = f"\n{summary}{suffix}"

    if skip and not folders[0] and not files[0]:
        # An out-of-range offset returns an empty page, which would otherwise
        # read exactly like an empty folder.
        return (
            f"{summary}\nNothing at --skip {skip}: this listing has "
            f"{folders[1]} folder(s) and {files[1]} file(s). Use --skip 0 to "
            "start from the beginning."
        )

    ranges: list[str] = []
    next_skip = 0
    for noun, (shown, total) in kinds:
        if shown and skip + shown < total:
            ranges.append(f"{noun}s {skip + 1}-{skip + shown} of {total}")
            next_skip = max(next_skip, skip + shown)
    if not ranges:
        return summary

    path = f" {target}" if target else ""
    return (
        f"{summary}\nShowing {', '.join(ranges)}."
        f"\nNext page: {command_prefix}ls{path} --skip {next_skip}"
    )


def cmd_ls(
    state: ShellState,
    target: str | None = None,
    skip: int = 0,
    *,
    command_prefix: str = "unique-cli ",
) -> str:
    """List folders and files at the given (or current) path.

    *skip* offsets both the folder and the file listing. *command_prefix* is
    prepended to the next-page command; the REPL passes ``""``.
    """
    if skip < 0:
        # The API rejects it (@Min(0) on both request DTOs).
        return "ls: --skip must be 0 or greater."
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
            _, content_ids = _collect_filter_targets(state.workspace_metadata_filter)
            # Only show folders that are actually browsable: a folder reachable
            # solely as an OR-alternative to a contentId allowlist is not a
            # standalone scope, so listing it would leak inventory. See
            # UN-21780.
            folder_ids = state.navigable_folder_ids()
            scoped_folders: list[Any] = []
            # Sliced before the fetch loop, so skipped ids cost no API calls.
            for sid in folder_ids[skip : skip + LS_LOCAL_PAGE_SIZE]:
                try:
                    scoped_folders.append(
                        unique_sdk.Folder.get_info(
                            user_id=state.config.user_id,
                            company_id=state.config.company_id,
                            scopeId=sid,
                        )
                    )
                except unique_sdk.UniqueError:
                    pass
            # A contentId mentioned in the filter is not necessarily in scope on
            # its own: an AND branch (e.g. contentId IN [x] AND folderIdPath A)
            # can exclude it. Verify against the full filter so root ls never
            # shows a title that read/cite and in-folder ls deny. Cached, so no
            # extra API cost. Filtered before the slice so --skip counts only
            # listable files. See UN-21780.
            in_scope_ids = [
                cid for cid in content_ids if state.is_content_within_workspace(cid)
            ]
            scoped_files: list[Any] = []
            for cid in in_scope_ids[skip : skip + LS_LOCAL_PAGE_SIZE]:
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
            return format_ls(scoped_folders, scoped_files) + _footer(
                skip,
                target,
                command_prefix,
                (len(scoped_folders), len(folder_ids)),
                (len(scoped_files), len(in_scope_ids)),
                suffix=" in task scope",
            )

        # When at root with a workspace restriction, show only the allowed scope
        # folders — the agent must not see the full company folder tree.
        if scope_id is None and state.workspace_scope_ids:
            folders: list[Any] = []
            for ws_id in state.workspace_scope_ids[skip : skip + LS_LOCAL_PAGE_SIZE]:
                try:
                    info = unique_sdk.Folder.get_info(
                        user_id=state.config.user_id,
                        company_id=state.config.company_id,
                        scopeId=ws_id,
                    )
                    folders.append(info)
                except unique_sdk.UniqueError:
                    pass
            total_ws = len(state.workspace_scope_ids)
            return format_ls(folders, []) + _footer(
                skip, target, command_prefix, (len(folders), total_ws), (0, 0)
            )

        folder_params: dict[str, Any] = {"skip": skip}
        content_params: dict[str, Any] = {"skip": skip}
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

        # Captured before the per-message filter narrows ``files``: truncation
        # is a property of the API page, not of the post-filter count.
        page_folders = len(folders)
        page_files = len(files)

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
            return format_ls(folders, files) + _footer(
                skip,
                target,
                command_prefix,
                (page_folders, total_folders),
                (page_files, total_files),
                summary=(
                    f"{_count(page_folders, total_folders, 'folder')}, "
                    f"{len(files)} file(s) in task scope "
                    f"(of {total_files} in folder)"
                ),
            )

        return format_ls(folders, files) + _footer(
            skip,
            target,
            command_prefix,
            (page_folders, total_folders),
            (page_files, total_files),
        )

    except (ValueError, unique_sdk.UniqueError) as e:
        return f"ls: {e}"
