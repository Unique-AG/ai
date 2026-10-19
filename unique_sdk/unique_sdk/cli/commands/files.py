"""File commands: upload, download, rm, rename (mv for files)."""

from __future__ import annotations

import mimetypes
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.commands.navigation import direct_children_filter
from unique_sdk.cli.formatting import format_content_info
from unique_sdk.cli.paths import canonical_folder_path, same_folder_path
from unique_sdk.cli.state import ShellState
from unique_sdk.utils.file_io import download_content, upload_file

# A denial result has the shape ``<command>: permission denied[…]`` (the
# command token is lowercase, e.g. ``upload``/``ls``/``restore-version``) and
# is always the *first thing* in the result string — each command returns the
# denial verbatim (e.g. ``"upload: permission denied: …"``, ``"read:
# permission denied: …"``). Anchor at the start of the string only: with
# re.MULTILINE, ``^`` would match the start of any line, so a multi-line
# *success* output containing a line shaped like ``token: permission denied``
# mid-result (e.g. quoted document text) would trigger a false non-zero exit.
# Successful results also start with a capitalised past-tense verb ("Uploaded:",
# "Downloaded:", "Renamed", "Restored:"), so the lowercase-prefix anchor never
# misfires on them. See UN-21780.
_PERMISSION_DENIED_RE = re.compile(r"^[a-z][a-z0-9-]*: permission denied")

_SUPPORTED_UPLOAD_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".html": "text/html",
    ".md": "text/markdown",
}

# Bounds so one name resolve can never page through the whole knowledge base.
_MAX_RESOLVE_MATCH_CANDIDATES = 100
_MAX_RESOLVE_INFOS_PAGES = 10
_RESOLVE_INFOS_PAGE_SIZE = 100
_MAX_RESOLVE_INFOS_ENTRIES = _MAX_RESOLVE_INFOS_PAGES * _RESOLVE_INFOS_PAGE_SIZE


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
    folder_path = state.cwd
    scope_id = state.scope_id
    if "/" in name_or_id:
        unique_path = _normalize_unique_file_path(state.cwd, name_or_id)
        folder_path, lookup_name = unique_path.rsplit("/", 1)
        if not lookup_name:
            raise ValueError(f"File path must include a file name: {name_or_id}")
        if not folder_path:
            folder_path = "/"
        # An active per-message filter replaces the static scopeIds for content
        # access. Gate the *folder* against the navigable filter scope before
        # Folder.get_info + the name scan: deferring solely to the per-id gate
        # lets a path into an out-of-scope folder resolve the file and surface a
        # task-scope "permission denied" instead of "File not found", leaking
        # cross-boundary existence — the same oracle closed for bare filenames
        # at root. The path check is structural (no API call), so it denies
        # uniformly whether or not the file exists. See UN-21780.
        if state.workspace_metadata_filter is not None:
            # Only gate the folder when the filter actually constrains folders.
            # A pure contentId scope has no navigable folders, so the document
            # may live anywhere and the per-id gate below is authoritative —
            # gating on folder here would wrongly deny it. When the filter does
            # name folders, a path outside them is denied structurally (no API
            # call), so an out-of-scope file can't leak existence via the per-id
            # "permission denied" vs "File not found" distinction.
            if (
                state.navigable_folder_ids()
                and not state.folder_path_allowed_by_metadata_filter(folder_path)
            ):
                raise ValueError(
                    f"permission denied: {name_or_id} is outside your task scope "
                    f"({state.scope_denial_hint()}). Use 'unique-cli search' or "
                    "'ls' within that scope instead."
                )
        elif not state.is_folder_target_within_workspace(folder_path):
            raise ValueError("permission denied (outside workspace scope)")

        info = unique_sdk.Folder.get_info(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            folderPath=folder_path,
        )
        scope_id = info.get("id")
        if not scope_id:
            raise ValueError(f"folder not found: {folder_path}")
    elif scope_id is None:
        # Resolving a bare name at the root would page the whole knowledge base.
        if state.workspace_metadata_filter is not None:
            # With a per-message filter active that is also a cross-scope
            # existence/title oracle. See UN-21780.
            raise ValueError(
                f"permission denied: {name_or_id} can't be resolved by name at "
                f"the knowledge-base root while a task scope is active "
                f"({state.scope_denial_hint()}). Use 'unique-cli search', cite "
                "by content id, or 'cd' into an in-scope folder."
            )
        if not state.is_within_workspace():
            raise ValueError("permission denied (outside workspace scope)")
        raise ValueError(
            f"{name_or_id} can't be resolved by name at the knowledge-base "
            "root. Use 'unique-cli search', pass a content id (cont_...), "
            "or 'cd' into a folder first."
        )

    return _resolve_content_id_in_folder(
        state=state,
        name_or_id=name_or_id,
        lookup_name=lookup_name,
        folder_path=folder_path,
        scope_id=scope_id,
        allow_chat_files=allow_chat_files,
    )


def _resolve_content_id_in_folder(
    *,
    state: ShellState,
    name_or_id: str,
    lookup_name: str,
    folder_path: str,
    scope_id: str,
    allow_chat_files: bool,
) -> tuple[str, str]:
    """Resolve ``lookup_name`` inside one folder without paging the whole KB."""
    match = _pick_match(
        hits=_hits_by_file_path(
            state=state,
            folder_path=folder_path,
            lookup_name=lookup_name,
            scope_id=scope_id,
        ),
        lookup_name=lookup_name,
    )
    capped = False
    if match is None:
        hits, capped = _hits_by_search(
            state=state, lookup_name=lookup_name, scope_id=scope_id
        )
        match = _pick_match(hits=hits, lookup_name=lookup_name)
    if match is None:
        if capped:
            raise ValueError(
                f"File not found in the first {_MAX_RESOLVE_INFOS_ENTRIES} "
                f"entries of this folder: {name_or_id}. Use 'unique-cli "
                "search' or pass a content id (cont_...)."
            )
        raise ValueError(f"File not found: {name_or_id}")

    resolved_id, display_name = match
    # Gate the *resolved* id too: resolving by file name or path must not
    # bypass the per-message metadata-filter scope that the cont_ fast-path
    # above enforces, and must honour the same read-only chat-file
    # exemption (so rm/mv by name can't reach an out-of-scope attachment
    # either). See UN-21780.
    if not state.is_content_within_workspace(
        resolved_id, allow_chat_files=allow_chat_files
    ):
        raise ValueError(
            f"permission denied: {name_or_id} is outside your "
            f"task scope ({state.scope_denial_hint()}). Use "
            "'unique-cli search' or 'ls' within that scope "
            "instead."
        )
    return resolved_id, display_name


def _hits_by_file_path(
    *, state: ShellState, folder_path: str, lookup_name: str, scope_id: str
) -> Sequence[Any]:
    # One indexed lookup that returns no chunks and also finds files whose
    # ingestion failed.
    try:
        result = unique_sdk.Content.get_info(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            filePath=f"{folder_path.rstrip('/')}/{lookup_name}",
        )
    except unique_sdk.UniqueError:
        return []
    # A server that ignores filePath returns unrelated content.
    return [
        info
        for info in result.get("contentInfo", [])
        if info.get("ownerId") == scope_id
    ]


def _hits_by_search(
    *, state: ShellState, lookup_name: str, scope_id: str
) -> tuple[Sequence[Any], bool]:
    """Return the hits, and whether the get_infos fallback hit its page cap."""
    try:
        hits = unique_sdk.Content.search(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            where={
                "AND": [
                    {"ownerId": {"equals": scope_id}},
                    {
                        "OR": [
                            {"title": {"equals": lookup_name}},
                            {"key": {"equals": lookup_name}},
                        ]
                    },
                ]
            },
            includeFailedContent=True,
        )
    except unique_sdk.UniqueError:
        return _resolve_content_id_via_infos_fallback(
            state=state,
            lookup_name=lookup_name,
            scope_id=scope_id,
        )
    return hits, False


def _pick_match(*, hits: Sequence[Any], lookup_name: str) -> tuple[str, str] | None:
    for content in hits[:_MAX_RESOLVE_MATCH_CANDIDATES]:
        info = _as_content_fields(content)
        resolved_id = info.get("id")
        if not isinstance(resolved_id, str) or not resolved_id:
            continue
        title = info.get("title") or ""
        key = info.get("key") or ""
        if lookup_name in {title, key}:
            return resolved_id, title or key
    return None


def _as_content_fields(content: Any) -> Mapping[str, Any]:
    if isinstance(content, Mapping):
        return content
    return {
        "id": getattr(content, "id", None),
        "title": getattr(content, "title", None),
        "key": getattr(content, "key", None),
    }


def _resolve_content_id_via_infos_fallback(
    *,
    state: ShellState,
    lookup_name: str,
    scope_id: str,
) -> tuple[list[Mapping[str, Any]], bool]:
    """Folder-scoped get_infos fallback with a hard page cap.

    Returns the match (if any), and whether the cap stopped the scan early.
    """
    skip = 0
    for _ in range(_MAX_RESOLVE_INFOS_PAGES):
        result = unique_sdk.Content.get_infos(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            metadataFilter=direct_children_filter(scope_id),
            skip=skip,
            take=_RESOLVE_INFOS_PAGE_SIZE,
        )
        content_infos = result.get("contentInfos", [])
        if not content_infos:
            return [], False
        for info in content_infos:
            title = info.get("title") or ""
            key = info.get("key") or ""
            if lookup_name in {title, key}:
                return [info], False
        if len(content_infos) < _RESOLVE_INFOS_PAGE_SIZE:
            return [], False
        skip += len(content_infos)
    return [], True


def _detect_upload_mime_type(path: Path) -> str:
    mime_type = _SUPPORTED_UPLOAD_MIME_TYPES.get(path.suffix.lower())
    if mime_type:
        return mime_type

    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


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
        try:
            actual = canonical_folder_path(
                state.config.user_id,
                state.config.company_id,
                resolved_id,
            )
        except (ValueError, unique_sdk.UniqueError) as e:
            raise ValueError(f"refused to upload to {folder_path}: {e}") from e
        if not same_folder_path(actual, folder_path):
            raise ValueError(
                f"refused to upload to {folder_path}: resolved to {actual}"
            )
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

        mime_type = _detect_upload_mime_type(path)

        result = upload_file(
            userId=state.config.user_id,
            companyId=state.config.company_id,
            path_to_file=str(path),
            displayed_filename=display_name,
            mime_type=mime_type,
            scope_or_unique_path=scope_id,
            versioning_enabled=True,
        )

        content_id = getattr(result, "id", None)
        if not content_id:
            return (
                f"upload: refused to upload {display_name} to {scope_id}: "
                "no content id returned"
            )
        folder_path = unique_sdk.Folder.get_folder_path(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            scope_id=scope_id,
        ).get("folderPath", scope_id)
        return f"Uploaded: {display_name} ({content_id}) to {folder_path}"

    except (ValueError, unique_sdk.UniqueError, OSError, RuntimeError) as e:
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
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"versions: {e}"


def cmd_restore_version(state: ShellState, content_version_id: str) -> str:
    """Restore a file from an archived content version ID."""
    # A per-message metaDataFilter is a hard task boundary, but the restore
    # API only resolves a contentVersionId to its content *after* mutating,
    # so an out-of-scope version can't be screened beforehand. Deny while a
    # filter is active rather than allow an unverifiable mutation; reads stay
    # gated regardless. The filter replaces the static scope for the turn, so
    # check it *before* the static is_within_workspace() fallback — otherwise
    # an out-of-static-scope cwd would surface the static denial (no task-scope
    # hint) even though the filter is authoritative. See UN-21780.
    if state.workspace_metadata_filter is not None:
        return (
            "restore-version: permission denied: cannot verify the target is "
            f"within your task scope ({state.scope_denial_hint()})."
        )
    if not state.is_within_workspace():
        return "restore-version: permission denied (outside workspace scope)"
    try:
        result = unique_sdk.Content.restore_version(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            contentVersionId=content_version_id,
        )
        title = result.get("title") or result.get("key") or result.get("id", "?")
        content_id = result.get("id", "?")
        return f"Restored: {title} ({content_id}) from version {content_version_id}"
    except (ValueError, unique_sdk.UniqueError) as e:
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

    except (ValueError, unique_sdk.UniqueError, OSError) as e:
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
    except (ValueError, unique_sdk.UniqueError) as e:
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
    except (ValueError, unique_sdk.UniqueError) as e:
        return f"mv: {e}"


def is_upload_error_output(output: str) -> bool:
    """Return True when *output* is a ``cmd_upload`` error.

    Success text is ``Uploaded: ...``. Local misses, missing destinations,
    and API failures all start with ``upload:`` and must exit non-zero.
    """
    return output.startswith("upload:")


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
