"""Navigation commands: cd, pwd, ls."""

from __future__ import annotations

from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_ls
from unique_sdk.cli.metadata_filter import _collect_filter_targets
from unique_sdk.cli.state import ShellState

# ``ls`` sends no ``take``: the page size is whatever the Public API serves by
# default. Page size is also not a user-facing flag -- choosing one well requires
# knowing the folder's size, which is what ``ls`` was run to discover, and a
# caller who guesses low gets a confident but incomplete picture. Nothing here
# assumes a particular page size: shown counts and the next ``--skip`` are all
# derived from the response lengths, so a change to the server default yields
# more or fewer pages rather than a wrong footer. See UN-24303.
#
# The two root-scoped branches below build their listing from explicit ids
# instead of a paginated query, so they need a local bound. It only has to keep
# output finite -- these lists hold one entry per configured task scope, far
# below the cap in practice -- and a client-side slice can never be rejected by
# the API, so it carries none of the risk of guessing the server's page size.
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
    """Render a count so a partial listing cannot read as a complete one.

    Collapses to the plain ``N noun(s)`` form when everything was listed, which
    keeps the common (unpaginated) summary line free of noise. See UN-24303.
    """
    if shown == total:
        return f"{shown} {noun}(s)"
    return f"{shown} of {total} {noun}(s)"


def _pagination_notice(
    *,
    skip: int,
    target: str | None,
    command_prefix: str,
    shown_folders: int,
    total_folders: int,
    shown_files: int,
    total_files: int,
) -> str:
    """Explain what a listing left out, and name the command that shows it.

    Folders and files paginate independently (two calls, two ``totalCount``s),
    so a kind is reported only when that kind was actually cut -- a folder with
    three subfolders and 212 files mentions only the files. ``--skip`` applies
    to both listings, so a single next-page command covers both.

    Returns ``""`` when the listing was complete and started at the top: small
    folders get no extra output. See UN-24303.
    """
    if skip and not shown_folders and not shown_files:
        # Prisma returns an empty page for an out-of-range offset while keeping
        # the real totalCount, so without this the output is indistinguishable
        # from a genuinely empty folder.
        return (
            f"\nNothing at --skip {skip}: this listing has {total_folders} "
            f"folder(s) and {total_files} file(s). Use --skip 0 to start from "
            "the beginning."
        )

    ranges: list[str] = []
    next_skip = 0
    for noun, shown, total in (
        ("folders", shown_folders, total_folders),
        ("files", shown_files, total_files),
    ):
        if shown and skip + shown < total:
            ranges.append(f"{noun} {skip + 1}-{skip + shown} of {total}")
            # Derived from what came back rather than from an assumed page
            # size, so the next page is right whatever the server serves.
            next_skip = max(next_skip, skip + shown)

    if not ranges:
        return ""

    path = f" {target}" if target else ""
    return (
        f"\nShowing {', '.join(ranges)}."
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
    prepended to the next-page command in the truncation notice; the REPL passes
    ``""`` so the hint is runnable as typed.
    """
    if skip < 0:
        # The API rejects a negative skip (@Min(0) on both request DTOs); fail
        # here so the caller gets a usable message instead of a 400.
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
            # This branch assembles its listing from explicit ids rather than a
            # paginated query, so page it locally: skipping before the get_info
            # loop keeps --skip honest here and avoids fetching what was skipped.
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
            # extra API cost. Filtering before the slice means --skip counts
            # only listable files. See UN-21780.
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
            output = format_ls(scoped_folders, scoped_files)
            summary = (
                f"\n{_count(len(scoped_folders), len(folder_ids), 'folder')}, "
                f"{_count(len(scoped_files), len(in_scope_ids), 'file')} "
                "in task scope"
            )
            return (
                output
                + summary
                + _pagination_notice(
                    skip=skip,
                    target=target,
                    command_prefix=command_prefix,
                    shown_folders=len(scoped_folders),
                    total_folders=len(folder_ids),
                    shown_files=len(scoped_files),
                    total_files=len(in_scope_ids),
                )
            )

        # When at root with a workspace restriction, show only the allowed scope
        # folders — the agent must not see the full company folder tree.
        if scope_id is None and state.workspace_scope_ids:
            folders: list[Any] = []
            # Also an explicit-id listing rather than a paginated query, so page
            # it locally for the same reason as the metadata-filter branch above.
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
            output = format_ls(folders, [])
            summary = f"\n{_count(len(folders), total_ws, 'folder')}, 0 file(s)"
            return (
                output
                + summary
                + _pagination_notice(
                    skip=skip,
                    target=target,
                    command_prefix=command_prefix,
                    shown_folders=len(folders),
                    total_folders=total_ws,
                    shown_files=0,
                    total_files=0,
                )
            )

        # No ``take``: inherit the server default rather than pin a page size
        # the API could later refuse. See LS_LOCAL_PAGE_SIZE above.
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

        # Page lengths as returned, captured before the per-message filter
        # narrows ``files``: pagination is a property of the API page, so the
        # notice must not be computed from the post-filter count.
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
            output = format_ls(folders, files)
            summary = (
                f"\n{_count(page_folders, total_folders, 'folder')}, "
                f"{len(files)} file(s) in task scope "
                f"(of {total_files} in folder)"
            )
            return (
                output
                + summary
                + _pagination_notice(
                    skip=skip,
                    target=target,
                    command_prefix=command_prefix,
                    shown_folders=page_folders,
                    total_folders=total_folders,
                    shown_files=page_files,
                    total_files=total_files,
                )
            )

        output = format_ls(folders, files)
        summary = (
            f"\n{_count(page_folders, total_folders, 'folder')}, "
            f"{_count(page_files, total_files, 'file')}"
        )
        return (
            output
            + summary
            + _pagination_notice(
                skip=skip,
                target=target,
                command_prefix=command_prefix,
                shown_folders=page_folders,
                total_folders=total_folders,
                shown_files=page_files,
                total_files=total_files,
            )
        )

    except (ValueError, unique_sdk.UniqueError) as e:
        return f"ls: {e}"
