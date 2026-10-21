"""Navigation commands: cd, pwd, ls."""

from __future__ import annotations

import shlex
from collections.abc import Callable, Mapping
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_ls
from unique_sdk.cli.metadata_filter import (
    _collect_filter_targets,
    direct_children_filter,
)
from unique_sdk.cli.paths import canonical_folder_path, same_folder_path
from unique_sdk.cli.state import ShellState

# Server take is capped at 100 and defaults to 50; ls pages to reach --limit rows.
LS_PAGE_SIZE = 100
LS_DEFAULT_LIMIT = 50
LS_MAX_LIMIT = 1000


def cmd_pwd(state: ShellState) -> str:
    return state.cwd


def cmd_cd(state: ShellState, target: str) -> str:
    """Change directory and return status message."""
    try:
        new_path = state.cd(target)
        return new_path
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"cd: {e}"


def _canonical_listing_error(
    state: ShellState,
    label: str,
    claimed_path: str,
    scope_id: str,
) -> str | None:
    """Return an ``ls:`` error when *scope_id* is not exactly *claimed_path*.

    ``get_info`` can hand back an ancestor for ``/home-<userId>/...``. The
    comparison runs before any rows are trusted, including when that ancestor
    has children. A failed lookup is an error: printing ``(empty)`` would hide
    it.
    """
    try:
        actual = canonical_folder_path(
            state.config.user_id,
            state.config.company_id,
            scope_id,
        )
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"ls: cannot list {label}: {e}"
    if not same_folder_path(actual, claimed_path):
        return (
            f"ls: cannot list {label}: resolved to {actual} instead (not listable here)"
        )
    return None


def _counts_without_rows_error(
    label: str,
    total_folders: int,
    total_files: int,
) -> str | None:
    """Return an ``ls:`` error when the API reports rows it did not return."""
    if total_folders or total_files:
        return (
            f"ls: cannot list {label}: listing returned no entries "
            f"({total_folders} folder(s), {total_files} file(s) reported)"
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


def _fetch_window(
    fetch_page: Callable[[int, int], Mapping[str, Any]],
    rows_key: str,
    skip: int,
    limit: int,
) -> tuple[list[Any], int]:
    """Return up to *limit* rows starting at *skip*, and the API total."""
    rows: list[Any] = []
    total: int | None = None
    offset = skip
    while len(rows) < limit:
        take = min(LS_PAGE_SIZE, limit - len(rows))
        result = fetch_page(offset, take)
        page = result.get(rows_key, [])
        total = result.get("totalCount", total)
        rows.extend(page)
        offset += len(page)
        if len(page) < take or (total is not None and offset >= total):
            break
    return rows, total if total is not None else skip + len(rows)


def _window_note(
    label: str,
    skip: int,
    limit: int,
    shown: dict[str, int],
    totals: dict[str, int],
    hidden_files: int = 0,
) -> str:
    """Say which rows this call read and how to list the rest; empty when complete.

    ``shown`` counts rows read from the server. ``hidden_files`` of them were
    dropped by the task scope and are not printed, so the wording says "read".
    """
    parts: list[str] = []
    for kind in ("folders", "files"):
        total = totals[kind]
        count = shown[kind]
        if total == 0 or (skip == 0 and count >= total):
            continue
        if count == 0:
            parts.append(f"no {kind} after {skip} (of {total})")
        else:
            parts.append(f"{kind} {skip + 1}-{skip + count} of {total}")
    if not parts:
        return ""
    verb = "read" if hidden_files else "showing"
    note = f"\n{verb} " + ", ".join(parts)
    if hidden_files:
        note += f" ({hidden_files} file(s) hidden by task scope)"
    if any(skip + shown[kind] < totals[kind] for kind in shown):
        quoted = shlex.quote(label)
        limit_arg = "" if limit == LS_DEFAULT_LIMIT else f" --limit {limit}"
        note += f"\nmore: unique-cli ls {quoted} --skip {skip + limit}{limit_arg}"
        # --all restarts at row 0, so it only helps when it would show more
        # than this window already does; at the cap it would repeat rows.
        if skip == 0 and limit < LS_MAX_LIMIT:
            note += f" (or: unique-cli ls {quoted} --all)"
    return note


def cmd_ls(
    state: ShellState,
    target: str | None = None,
    *,
    skip: int = 0,
    limit: int = LS_DEFAULT_LIMIT,
    all_items: bool = False,
) -> str:
    """List folders and files at the given (or current) path.

    Shows up to *limit* folders and *limit* files starting at *skip*
    (``all_items`` raises *limit* to ``LS_MAX_LIMIT``). When more exist, the
    output says which rows are shown and ends with the ``ls`` call for the rest.
    """
    if all_items and limit != LS_DEFAULT_LIMIT:
        return "ls: --all and --limit cannot be combined"
    if all_items:
        limit = LS_MAX_LIMIT
    if skip < 0:
        return "ls: --skip must be 0 or more"
    if not 1 <= limit <= LS_MAX_LIMIT:
        return f"ls: --limit must be between 1 and {LS_MAX_LIMIT}"
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

        # The scoped root lists a fixed set of folders; there is nothing to page.
        if (
            scope_id is None
            and skip
            and (
                state.workspace_metadata_filter is not None or state.workspace_scope_ids
            )
        ):
            return "ls: paging is not supported at the scoped root"

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

        if scope_id:
            label = target if target is not None else resolved_path
            path_error = _canonical_listing_error(
                state,
                label,
                resolved_path,
                scope_id,
            )
            if path_error:
                return path_error

        folder_params: dict[str, Any] = {}
        if scope_id:
            folder_params["parentId"] = scope_id

        folders, total_folders = _fetch_window(
            lambda offset, take: unique_sdk.Folder.get_infos(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                skip=offset,
                take=take,
                **folder_params,
            ),
            "folderInfos",
            skip,
            limit,
        )
        # Every file lives in a folder, so the root has no files of its own.
        files: list[Any] = []
        total_files = 0
        if scope_id:
            files, total_files = _fetch_window(
                lambda offset, take: unique_sdk.Content.get_infos(
                    user_id=state.config.user_id,
                    company_id=state.config.company_id,
                    metadataFilter=direct_children_filter(scope_id),
                    skip=offset,
                    take=take,
                ),
                "contentInfos",
                skip,
                limit,
            )

        if scope_id and not folders and not files and skip == 0:
            label = target if target is not None else resolved_path
            counts_error = _counts_without_rows_error(
                label,
                total_folders,
                total_files,
            )
            if counts_error:
                return counts_error

        # With a per-message filter, listing inside an allowed folder must not
        # reveal files the filter excludes (e.g. a combined folder + contentId
        # allowlist): read/cite would deny them, so ls must hide them too.
        # Folder-only filters keep every file (each passes the folderIdPath
        # leaf); the verdict is cached per content id. See UN-21780.
        # The paging note counts rows read from the server, before the scope filter.
        scanned_files = len(files)
        if state.workspace_metadata_filter is not None:
            files = [
                f for f in files if state.is_content_within_workspace(f.get("id", ""))
            ]
        note = _window_note(
            target if target is not None else resolved_path,
            skip,
            limit,
            {"folders": len(folders), "files": scanned_files},
            {"folders": total_folders, "files": total_files},
            hidden_files=scanned_files - len(files),
        )

        output = format_ls(folders, files)
        if state.workspace_metadata_filter is not None:
            # ``files`` is only the current API page, so the in-scope count is
            # per-page, not the folder total. Report it as the shown-in-scope
            # count and keep the API ``totalCount`` as the folder's real size,
            # rather than overwriting total_files with the page length (which
            # would silently undercount paginated folders). See UN-21780.
            summary = (
                f"\n{total_folders} folder(s), {len(files)} file(s) in task scope "
                f"(of {total_files} in folder)"
            )
            return output + summary + note

        summary = f"\n{total_folders} folder(s), {total_files} file(s)"
        return output + summary + note

    except (ValueError, unique_sdk.UniqueError) as e:
        return f"ls: {e}"
