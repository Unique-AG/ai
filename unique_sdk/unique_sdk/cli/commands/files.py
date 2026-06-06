"""File commands: upload, download, rm, rename (mv for files)."""

from __future__ import annotations

import mimetypes
import posixpath
import shutil
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_content_info
from unique_sdk.cli.state import ShellState
from unique_sdk.utils.file_io import download_content, upload_file


def _resolve_content_id(state: ShellState, name_or_id: str) -> tuple[str, str]:
    """Resolve a file name or content ID to (content_id, display_name).

    Accepts a content ID (cont_...), a file name in the current folder,
    or an absolute/relative Unique file path.
    """
    if name_or_id.startswith("cont_"):
        return name_or_id, name_or_id

    lookup_name = name_or_id
    scope_id = state.scope_id
    # Preserve support for unusual literal filenames like "../../.bashrc".
    # Only resolve slash-containing values as Unique paths when they are not
    # path traversal shaped names.
    if "/" in name_or_id and ".." not in name_or_id.split("/"):
        folder_path, lookup_name = name_or_id.rsplit("/", 1)
        if not lookup_name:
            raise ValueError(f"File path must include a file name: {name_or_id}")
        if not folder_path:
            folder_path = "/"
        elif not folder_path.startswith("/"):
            folder_path = f"{state.cwd.rstrip('/')}/{folder_path}"
        folder_path = posixpath.normpath(folder_path)

        info = unique_sdk.Folder.get_info(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            folderPath=folder_path,
        )
        scope_id = info.get("id")
        if not scope_id:
            raise ValueError(f"folder not found: {folder_path}")

    params: dict[str, Any] = {}
    if scope_id:
        params["parentId"] = scope_id

    result = unique_sdk.Content.get_infos(
        user_id=state.config.user_id,
        company_id=state.config.company_id,
        **params,
    )
    for info in result.get("contentInfos", []):
        title = info.get("title") or info.get("key") or ""
        if title == lookup_name:
            return info["id"], title

    raise ValueError(f"File not found: {name_or_id}")


def _format_version_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _format_content_versions(versions: list[dict[str, Any]]) -> str:
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
    if not state.is_folder_target_within_workspace(dest):
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
    if name_or_id.startswith("cont_"):
        if not state.is_content_within_workspace(name_or_id):
            return "rm: permission denied (outside workspace scope)"
    elif not state.is_within_workspace():
        return "rm: permission denied (outside workspace scope)"
    try:
        content_id, display_name = _resolve_content_id(state, name_or_id)
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
    if old_name.startswith("cont_"):
        if not state.is_content_within_workspace(old_name):
            return "mv: permission denied (outside workspace scope)"
    elif not state.is_within_workspace():
        return "mv: permission denied (outside workspace scope)"
    try:
        content_id, display_name = _resolve_content_id(state, old_name)
        result = unique_sdk.Content.update(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
            contentId=content_id,
            title=new_name,
        )
        return f"Renamed: {display_name} -> {result.get('title', new_name)}\n{format_content_info(result)}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"mv: {e}"
