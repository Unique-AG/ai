"""Download knowledge-base scope contents into a local folder."""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import typer
from unique_sdk import Content, Folder
from unique_sdk.cli.config import Config
from unique_sdk.utils.file_io import download_content

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure

_PAGE_SIZE = 100


def _list_content_infos(cfg: Config, scope_id: str) -> list[Content.ContentInfo]:
    """Return all content infos in a folder scope (paginated)."""
    infos: list[Content.ContentInfo] = []
    skip = 0
    while True:
        page = Content.get_infos(
            cfg.user_id,
            cfg.company_id,
            parentId=scope_id,
            skip=skip,
            take=_PAGE_SIZE,
        )
        batch = page.get("contentInfos") or []
        infos.extend(batch)
        skip += len(batch)
        if not batch or skip >= page.get("totalCount", 0):
            break
    return infos


def _list_child_folders(cfg: Config, scope_id: str) -> list[Folder.FolderInfo]:
    """Return all child folder infos under a scope (paginated)."""
    folders: list[Folder.FolderInfo] = []
    skip = 0
    while True:
        page = Folder.get_infos(
            cfg.user_id,
            cfg.company_id,
            parentId=scope_id,
            skip=skip,
            take=_PAGE_SIZE,
        )
        batch = page.get("folderInfos") or []
        folders.extend(batch)
        skip += len(batch)
        if not batch or skip >= page.get("totalCount", 0):
            break
    return folders


def _join_rel_subdir(parent: str, child_name: str) -> str:
    parent = parent.strip()
    child_name = child_name.strip()
    if parent == "":
        return child_name
    return f"{parent}/{child_name}"


def _safe_local_path(local_dir: Path, *parts: str) -> Path | None:
    """Join ``parts`` under ``local_dir``, guarding against path traversal.

    ``key`` and recursive folder names come from remote KB metadata and are not
    trusted. A crafted value containing ``..`` segments or a leading ``/`` could
    otherwise escape the destination. Returns the resolved path when it stays
    inside ``local_dir``, or ``None`` when it would escape.
    """
    base = local_dir.resolve()
    candidate = base
    for part in parts:
        candidate = candidate / part
    candidate = candidate.resolve()
    if candidate == base or base in candidate.parents:
        return candidate
    return None


def cmd_download(
    cfg: Config,
    *,
    local_dir: Path,
    folder_path: str | None,
    scope_id: str | None,
    recursive: bool,
    dry_run: bool,
) -> None:
    if bool(folder_path) == bool(scope_id):
        typer.echo("Specify exactly one of --folder-path or --scope-id.", err=True)
        sys.exit(2)

    if folder_path and not folder_path.startswith("/"):
        typer.echo(
            f"--folder-path must be an absolute path (start with '/'): {folder_path}",
            err=True,
        )
        sys.exit(2)

    if folder_path:
        try:
            resolved_scope_id = Folder.resolve_scope_id_from_folder_path(
                cfg.user_id, cfg.company_id, folder_path=folder_path
            )
        except Exception as exc:
            typer.echo(f"failed to resolve folder {folder_path!r}: {exc}", err=True)
            echo_credential_debug_if_auth_failure(cfg, exc, label="kb download")
            sys.exit(1)
        if resolved_scope_id is None:
            typer.echo(f"failed to resolve folder {folder_path!r}: not found", err=True)
            sys.exit(1)
        base_scope_id = resolved_scope_id
    else:
        assert scope_id is not None
        try:
            _ = Folder.get_folder_path(cfg.user_id, cfg.company_id, scope_id)
        except Exception as exc:
            typer.echo(f"failed to resolve scope {scope_id!r}: {exc}", err=True)
            echo_credential_debug_if_auth_failure(cfg, exc, label="kb download")
            sys.exit(1)
        base_scope_id = scope_id

    if not dry_run:
        local_dir.mkdir(parents=True, exist_ok=True)

    queue: deque[tuple[str, str]] = deque([(base_scope_id, "")])
    counts = {"downloaded": 0, "failed": 0}

    while queue:
        current_scope_id, rel_subdir = queue.popleft()

        for info in _list_content_infos(cfg, current_scope_id):
            key = info["key"]
            content_id = info["id"]
            display = key if rel_subdir == "" else f"{rel_subdir}/{key}"
            parts = (rel_subdir, key) if rel_subdir else (key,)
            local_path = _safe_local_path(local_dir, *parts)
            if local_path is None:
                typer.echo(
                    f"failed: {display}: refusing to write outside {local_dir}",
                    err=True,
                )
                counts["failed"] += 1
                continue

            if dry_run:
                typer.echo(f"[dry-run] downloaded: {display}")
                counts["downloaded"] += 1
                continue

            try:
                _ = download_content(
                    companyId=cfg.company_id,
                    userId=cfg.user_id,
                    content_id=content_id,
                    filename=key,
                    target_path=local_path,
                )
            except Exception as exc:
                typer.echo(f"failed: {display}: {exc}", err=True)
                echo_credential_debug_if_auth_failure(cfg, exc, label="kb download")
                counts["failed"] += 1
                continue

            typer.echo(f"downloaded: {display}")
            counts["downloaded"] += 1

        if recursive:
            for folder_info in _list_child_folders(cfg, current_scope_id):
                child_scope_id = folder_info["id"]
                child_name = folder_info["name"]
                queue.append((child_scope_id, _join_rel_subdir(rel_subdir, child_name)))

    if counts["downloaded"] == 0 and counts["failed"] == 0:
        typer.echo("No files to download.")
        return

    typer.echo(f"Done: {counts['downloaded']} downloaded, {counts['failed']} failed.")
    if counts["failed"]:
        sys.exit(1)
