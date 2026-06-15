"""File commands: upload, download, rm, rename (mv for files)."""

from __future__ import annotations

import mimetypes
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_content_info
from unique_sdk.cli.state import ShellState
from unique_sdk.utils.file_io import download_content, upload_file

# A denial result has the shape ``<command>: permission denied[…]`` (the
# command token is lowercase, e.g. ``upload``/``ls``/``restore-version``).
# Successful results start with a capitalised past-tense verb ("Uploaded:",
# "Downloaded:", "Renamed", "Restored:"), so anchoring on a lowercase command
# prefix matches every denial without misfiring on a success line that merely
# contains the phrase (e.g. a filename). MULTILINE so a wrapped multi-line
# result still matches. See UN-21780.
_PERMISSION_DENIED_RE = re.compile(r"^[a-z][a-z0-9-]*: permission denied", re.MULTILINE)


def _normalize_unique_file_path(cwd: str, path: str) -> str:
    """Normalize a Unique file path without allowing traversal above root."""
    raw_parts = (
        path.split("/") if path.startswith("/") else [*cwd.split("/"), *path.split("/")]
    )
    parts: list[str] = []
    for part in raw_parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError(f"File path escapes root: {path}")
            parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts)


def _resolve_content_id(
    state: ShellState, name_or_id: str, *, allow_chat_files: bool = True
) -> tuple[str, str]:
    """Resolve a file name or content ID to (content_id, display_name).

    Accepts a content ID (cont_...), a file name in the current folder,
    or an absolute/relative Unique file path. Pass ``allow_chat_files=False``
    from destructive ops so the chat-attachment exemption (read-only intent)
    can't be used to delete/rename out-of-scope content. See UN-21780.
    """
    if name_or_id.startswith("cont_"):
        if not state.is_content_within_workspace(
            name_or_id, allow_chat_files=allow_chat_files
        ):
            raise ValueError(
                f"permission denied: {name_or_id} is outside your task scope "
                f"({state.scope_denial_hint()}). Use 'unique-cli search' or "
                "'ls' within that scope instead."
            )
        return name_or_id, name_or_id

    lookup_name = name_or_id
    scope_id = state.scope_id
    if "/" in name_or_id:
        unique_path = _normalize_unique_file_path(state.cwd, name_or_id)
        folder_path, lookup_name = unique_path.rsplit("/", 1)
        if not lookup_name:
            raise ValueError(f"File path must include a file name: {name_or_id}")
        if not folder_path:
            folder_path = "/"
        # An active per-message filter replaces the static scopeIds for content
        # access, so the static folder check must not over-deny an in-filter
        # path; the resolved content id is gated by is_content_within_workspace
        # below either way. See UN-21780.
        if (
            state.workspace_metadata_filter is None
            and not state.is_folder_target_within_workspace(folder_path)
        ):
            raise ValueError("permission denied (outside workspace scope)")

        info = unique_sdk.Folder.get_info(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            folderPath=folder_path,
        )
        scope_id = info.get("id")
        if not scope_id:
            raise ValueError(f"folder not found: {folder_path}")
    elif state.workspace_metadata_filter is None and not state.is_within_workspace():
        # See above: defer to the filter (enforced on the resolved id) when one
        # is active rather than over-denying via static scopeIds. UN-21780.
        raise ValueError("permission denied (outside workspace scope)")

    params: dict[str, Any] = {}
    if scope_id:
        params["parentId"] = scope_id

    take = 100
    skip = 0
    while True:
        result = unique_sdk.Content.get_infos(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            skip=skip,
            take=take,
            **params,
        )
        content_infos = result.get("contentInfos", [])
        if not content_infos:
            break

        for info in content_infos:
            title = info.get("title") or ""
            key = info.get("key") or ""
            if lookup_name in {title, key}:
                resolved_id = info["id"]
                # Gate the *resolved* id too: resolving by file name or path
                # must not bypass the per-message metadata-filter scope that
                # the cont_ fast-path above enforces, and must honour the same
                # read-only chat-file exemption (so rm/mv by name can't reach
                # an out-of-scope attachment either). See UN-21780.
                if not state.is_content_within_workspace(
                    resolved_id, allow_chat_files=allow_chat_files
                ):
                    raise ValueError(
                        f"permission denied: {name_or_id} is outside your "
                        f"task scope ({state.scope_denial_hint()}). Use "
                        "'unique-cli search' or 'ls' within that scope "
                        "instead."
                    )
                return resolved_id, title or key

        skip += len(content_infos)

    raise ValueError(f"File not found: {name_or_id}")


def _format_version_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _format_content_versions(versions: Sequence[Mapping[str, Any]]) -> str:
    if not versions:
        return "No versions found."

    lines = ["VERSION  VERSION_ID  ARCHIVED_AT  REASON  TITLE"]
    for version in versions:
        lines.append(
            "  ".join(
                [
                    _format_version_value(version.get("versionNumber")),
                    _format_version_value(version.get("id")),
                    _format_version_value(version.get("archivedAt")),
                    _format_version_value(version.get("reason")),
                    _format_version_value(version.get("title") or version.get("key")),
                ]
            )
        )
    return "\n".join(lines)


def _resolve_upload_destination(
    state: ShellState,
    local_filename: str,
    destination: str | None,
) -> tuple[str, str]:
    """Resolve the upload destination into (scope_id, display_name).

    Behaves like Linux cp:
      None            -> current dir, original filename
      "."             -> current dir, original filename
      "newname.pdf"   -> current dir, renamed file
      "subfolder/"    -> subfolder, original filename
      "./subfolder/"  -> subfolder, original filename
      "subfolder/new" -> subfolder, renamed file
      "/abs/path/"    -> absolute folder, original filename
      scope_abc123    -> that scope, original filename

    A bare "/" (or only slashes) is rejected: it would otherwise strip to an
    empty path and be mis-resolved relative to cwd.
    """
    if destination is None or destination == ".":
        scope_id = state.scope_id
        if not scope_id:
            raise ValueError("cannot upload to root. cd into a folder first.")
        return scope_id, local_filename

    if destination.startswith("scope_"):
        return destination, local_filename

    if "/" in destination:
        if destination.endswith("/"):
            folder_path = destination.rstrip("/")
            display_name = local_filename
        else:
            parts = destination.rsplit("/", 1)
            folder_path = parts[0] if parts[0] else "/"
            display_name = parts[1]

        if not folder_path:
            raise ValueError("cannot upload to root. cd into a folder first.")

        if folder_path == ".":
            scope_id = state.scope_id
            if not scope_id:
                raise ValueError("cannot upload to root. cd into a folder first.")
            return scope_id, display_name

        if not folder_path.startswith("/"):
            folder_path = f"{state.cwd.rstrip('/')}/{folder_path}"

        info = unique_sdk.Folder.get_info(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            folderPath=folder_path,
        )
        resolved_id = info.get("id")
        if not resolved_id:
            raise ValueError(f"folder not found: {folder_path}")
        return resolved_id, display_name

    scope_id = state.scope_id
    if not scope_id:
        raise ValueError("cannot upload to root. cd into a folder first.")
    return scope_id, destination


def cmd_upload(
    state: ShellState,
    local_path: str,
    destination: str | None = None,
) -> str:
    """Upload a local file. Destination works like Linux cp.

    upload file.pdf              -> current dir, keeps name
    upload file.pdf .            -> current dir, keeps name
    upload file.pdf new.pdf      -> current dir, renamed
    upload file.pdf subfolder/   -> into subfolder, keeps name
    upload file.pdf ./sub/new.pdf -> into sub, renamed
    upload file.pdf /abs/path/   -> into absolute path folder
    """
    dest = destination or "."
    # A per-message metaDataFilter *replaces* the static scopeIds (read/search/
    # ls honour the filter, not scopeIds), so the static-scope check must not
    # over-deny an in-filter destination. When a filter is active the resolved
    # scope id is gated against it below instead. See UN-21780.
    if (
        state.workspace_metadata_filter is None
        and not state.is_folder_target_within_workspace(dest)
    ):
        return "upload: permission denied (outside workspace scope)"
    try:
        path = Path(local_path).expanduser().resolve()
        if not path.is_file():
            return f"upload: local file not found: {local_path}"

        scope_id, display_name = _resolve_upload_destination(
            state,
            path.name,
            destination,
        )

        # is_folder_target_within_workspace only enforces the static
        # scopeIds; when the runner supplies a per-message metaDataFilter
        # without scopeIds it treats every folder as writable. Gate the
        # resolved destination against the per-message filter too, so uploads
        # can't escape a task scope that read/download/ls/search honor.
        # See UN-21780.
        if (
            state.workspace_metadata_filter is not None
            and not state.folder_allowed_by_metadata_filter(scope_id)
        ):
            return (
                "upload: permission denied: destination is outside your "
                f"task scope ({state.scope_denial_hint()})."
            )

        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"

        result = upload_file(
            userId=state.config.user_id,
            companyId=state.config.company_id,
            path_to_file=str(path),
            displayed_filename=display_name,
            mime_type=mime_type,
            scope_or_unique_path=scope_id,
            versioning_enabled=True,
        )

        content_id = result.id if hasattr(result, "id") else "?"
        folder_path = unique_sdk.Folder.get_folder_path(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            scope_id=scope_id,
        ).get("folderPath", scope_id)
        return f"Uploaded: {display_name} ({content_id}) to {folder_path}"

    except (ValueError, unique_sdk.APIError, OSError) as e:
        return f"upload: {e}"


def cmd_versions(
    state: ShellState,
    name_or_id: str,
    skip: int | None = None,
    take: int | None = None,
) -> str:
    """List archived versions for a file by name or content ID."""
    try:
        content_id, display_name = _resolve_content_id(state, name_or_id)
        params: dict[str, Any] = {"contentId": content_id}
        if skip is not None:
            params["skip"] = skip
        if take is not None:
            params["take"] = take

        result = unique_sdk.Content.versions(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            **params,
        )
        data = result.get("data", [])
        return f"Versions for {display_name} ({content_id}):\n{_format_content_versions(data)}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"versions: {e}"


def cmd_restore_version(state: ShellState, content_version_id: str) -> str:
    """Restore a file from an archived content version ID."""
    if not state.is_within_workspace():
        return "restore-version: permission denied (outside workspace scope)"
    # A per-message metaDataFilter is a hard task boundary, but the restore
    # API only resolves a contentVersionId to its content *after* mutating,
    # so an out-of-scope version can't be screened beforehand. Deny while a
    # filter is active rather than allow an unverifiable mutation; reads stay
    # gated regardless. See UN-21780.
    if state.workspace_metadata_filter is not None:
        return (
            "restore-version: permission denied: cannot verify the target is "
            f"within your task scope ({state.scope_denial_hint()})."
        )
    try:
        result = unique_sdk.Content.restore_version(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            contentVersionId=content_version_id,
        )
        title = result.get("title") or result.get("key") or result.get("id", "?")
        content_id = result.get("id", "?")
        return f"Restored: {title} ({content_id}) from version {content_version_id}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"restore-version: {e}"


def cmd_download(
    state: ShellState,
    name_or_id: str,
    local_dest: str | None = None,
) -> str:
    """Download a file by name or content ID."""
    try:
        content_id, display_name = _resolve_content_id(state, name_or_id)

        raw_name = (
            display_name if not display_name.startswith("cont_") else f"{content_id}"
        )
        filename = Path(raw_name).name
        downloaded_path = download_content(
            companyId=state.config.company_id,
            userId=state.config.user_id,
            content_id=content_id,
            filename=filename,
        )

        if local_dest:
            dest = Path(local_dest).expanduser().resolve()
            if dest.is_dir():
                dest = dest / filename
            shutil.move(str(downloaded_path), str(dest))
            return f"Downloaded: {display_name} -> {dest}"

        final_dest = Path.cwd() / filename
        shutil.move(str(downloaded_path), str(final_dest))
        return f"Downloaded: {display_name} -> {final_dest}"

    except (ValueError, unique_sdk.APIError, OSError) as e:
        return f"download: {e}"


def cmd_rm(state: ShellState, name_or_id: str) -> str:
    """Delete a file by name or content ID."""
    try:
        # Destructive: allow_chat_files=False so the chat-attachment read
        # exemption can't be used to delete an out-of-scope file. Resolution
        # also surfaces the task-scope hint on denial. See UN-21780.
        content_id, display_name = _resolve_content_id(
            state, name_or_id, allow_chat_files=False
        )
        unique_sdk.Content.delete(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            contentId=content_id,
        )
        return f"Deleted: {display_name} ({content_id})"
    except (ValueError, unique_sdk.APIError) as e:
        return f"rm: {e}"


def cmd_mv_file(state: ShellState, old_name: str, new_name: str) -> str:
    """Rename a file."""
    try:
        # Destructive: allow_chat_files=False so the chat-attachment read
        # exemption can't be used to rename an out-of-scope file. Resolution
        # also surfaces the task-scope hint on denial. See UN-21780.
        content_id, display_name = _resolve_content_id(
            state, old_name, allow_chat_files=False
        )
        result = unique_sdk.Content.update(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            contentId=content_id,
            title=new_name,
        )
        return f"Renamed: {display_name} -> {result.get('title', new_name)}\n{format_content_info(result)}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"mv: {e}"


def is_permission_denied_output(output: str) -> bool:
    """Return ``True`` when a file-op result is a permission/scope denial.

    Lets the one-shot dispatcher exit non-zero so shell ``&&`` chains stop on
    an out-of-scope content access instead of continuing as if it succeeded.

    Matches the denial only when it is the *form of the result* — a
    ``<command>: permission denied`` line — rather than anywhere the substring
    appears. Denials are emitted as ``"<cmd>: permission denied[ : …]"`` (e.g.
    ``"upload: permission denied: …"``); anchoring on that shape avoids a
    false non-zero exit when a successful result happens to contain the phrase
    (e.g. a filename or document text). See UN-21780.
    """
    return bool(_PERMISSION_DENIED_RE.search(output))
