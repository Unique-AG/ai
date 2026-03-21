"""File commands: upload, download, rm, rename (mv for files)."""

from __future__ import annotations

import mimetypes
import shutil
from pathlib import Path
from typing import Any

import unique_sdk
from unique_sdk.cli.formatting import format_content_info
from unique_sdk.cli.state import ShellState
from unique_sdk.utils.file_io import download_content, upload_file


def _resolve_content_id(state: ShellState, name_or_id: str) -> tuple[str, str]:
    """Resolve a file name or content ID to (content_id, display_name).

    Accepts either a content ID (cont_...) or a file name/path.
    """
    if name_or_id.startswith("cont_"):
        return name_or_id, name_or_id

    scope_id = state.scope_id
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
        if title == name_or_id:
            return info["id"], title

    raise ValueError(f"File not found: {name_or_id}")


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
