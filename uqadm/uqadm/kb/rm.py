"""Delete knowledge-base folders or individual files from a scope."""

from __future__ import annotations

import sys
from collections import deque

import typer
from unique_sdk import Content, Folder
from unique_sdk.cli.config import Config

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


def _collect_subtree(cfg: Config, scope_id: str) -> tuple[list[str], list[str]]:
    """Return ``(file_paths, folder_paths)`` for the whole subtree under a scope.

    Both lists hold display paths relative to the root scope (the root folder
    itself is excluded). Used to render an accurate ``--recursive`` delete plan,
    since ``Folder.delete(recursive=True)`` removes the entire subtree, not just
    the top level.
    """
    files: list[str] = []
    folders: list[str] = []
    queue: deque[tuple[str, str]] = deque([(scope_id, "")])
    while queue:
        current_scope_id, rel = queue.popleft()
        for info in _list_content_infos(cfg, current_scope_id):
            files.append(f"{rel}/{info['key']}" if rel else info["key"])
        for folder_info in _list_child_folders(cfg, current_scope_id):
            child_rel = f"{rel}/{folder_info['name']}" if rel else folder_info["name"]
            folders.append(child_rel)
            queue.append((folder_info["id"], child_rel))
    return files, folders


def _report(counts: dict[str, int]) -> None:
    typer.echo(
        f"Done: {counts['deleted']} deleted, {counts['not_found']} not found, "
        f"{counts['failed']} failed."
    )
    if counts["failed"]:
        sys.exit(1)


def _rm_files(
    cfg: Config,
    scope_id: str,
    target_label: str,
    files: list[str],
    *,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    try:
        infos = _list_content_infos(cfg, scope_id)
    except Exception as exc:
        typer.echo(f"failed to list contents of {target_label!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
        sys.exit(1)

    # A folder may legitimately hold several files with the same key; delete all
    # matches so a targeted removal doesn't leave duplicates behind.
    by_key: dict[str, list[str]] = {}
    for info in infos:
        by_key.setdefault(info["key"], []).append(info["id"])

    matched = [name for name in files if name in by_key]

    # None of the requested files exist: report and fail regardless of dry-run,
    # so automation validating targets with --dry-run sees the same exit code as
    # a real run.
    if not matched:
        for name in files:
            typer.echo(f"not found: {name}")
        typer.echo("No matching files to delete.")
        sys.exit(1)

    if dry_run:
        counts = {"deleted": 0, "not_found": 0, "failed": 0}
        for name in files:
            ids = by_key.get(name)
            if not ids:
                typer.echo(f"not found: {name}")
                counts["not_found"] += 1
                continue
            for _cid in ids:
                typer.echo(f"[dry-run] deleted: {name}")
                counts["deleted"] += 1
        _report(counts)
        return

    if not assume_yes:
        total = sum(len(by_key[name]) for name in matched)
        typer.echo(f"About to delete {total} file(s) from {target_label}:")
        for name in matched:
            typer.echo(f"  {name}")
        if not typer.confirm("Proceed?"):
            typer.echo("Aborted.")
            sys.exit(1)

    counts = {"deleted": 0, "not_found": 0, "failed": 0}
    for name in files:
        ids = by_key.get(name)
        if not ids:
            typer.echo(f"not found: {name}")
            counts["not_found"] += 1
            continue
        for content_id in ids:
            try:
                Content.delete(cfg.user_id, cfg.company_id, contentId=content_id)
            except Exception as exc:
                typer.echo(f"failed: {name}: {exc}", err=True)
                echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
                counts["failed"] += 1
                continue
            typer.echo(f"deleted: {name}")
            counts["deleted"] += 1

    _report(counts)


def _rm_folder(
    cfg: Config,
    scope_id: str,
    target_label: str,
    *,
    recursive: bool,
    dry_run: bool,
    assume_yes: bool,
) -> None:
    try:
        contents = _list_content_infos(cfg, scope_id)
        child_folders = _list_child_folders(cfg, scope_id)
    except Exception as exc:
        typer.echo(f"failed to inspect folder {target_label!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
        sys.exit(1)

    # A non-empty folder is only removable with --recursive; refuse otherwise so
    # a stray `kb rm` can't wipe a populated folder by surprise.
    if (contents or child_folders) and not recursive:
        typer.echo(
            f"refusing to delete non-empty folder {target_label!r} "
            f"({len(contents)} file(s), {len(child_folders)} subfolder(s)); "
            f"pass --recursive/-r to delete it and everything under it.",
            err=True,
        )
        sys.exit(2)

    if dry_run:
        if recursive:
            # Walk the full subtree so the plan reflects everything
            # Folder.delete(recursive=True) will remove, not just the top level.
            try:
                files, subfolders = _collect_subtree(cfg, scope_id)
            except Exception as exc:
                typer.echo(
                    f"failed to inspect folder {target_label!r}: {exc}", err=True
                )
                echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
                sys.exit(1)
        else:
            files = [info["key"] for info in contents]
            subfolders = [folder_info["name"] for folder_info in child_folders]
        for display in files:
            typer.echo(f"[dry-run] deleted file: {display}")
        for display in subfolders:
            typer.echo(f"[dry-run] deleted subfolder: {display}")
        typer.echo(f"[dry-run] deleted folder: {target_label}")
        return

    if not assume_yes:
        prompt = (
            f"Delete folder {target_label} and everything under it?"
            if recursive
            else f"Delete folder {target_label}?"
        )
        if not typer.confirm(prompt):
            typer.echo("Aborted.")
            sys.exit(1)

    try:
        Folder.delete(
            cfg.user_id, cfg.company_id, scopeId=scope_id, recursive=recursive
        )
    except Exception as exc:
        typer.echo(f"failed to delete folder {target_label!r}: {exc}", err=True)
        echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
        sys.exit(1)

    typer.echo(f"deleted folder: {target_label}")


def cmd_rm(
    cfg: Config,
    *,
    folder_path: str | None,
    scope_id: str | None,
    files: tuple[str, ...],
    recursive: bool,
    dry_run: bool,
    assume_yes: bool,
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

    # Reduce both entry points to a scope id plus a human-readable label.
    if folder_path:
        try:
            resolved_scope_id = Folder.resolve_scope_id_from_folder_path(
                cfg.user_id, cfg.company_id, folder_path=folder_path
            )
        except Exception as exc:
            typer.echo(f"failed to resolve folder {folder_path!r}: {exc}", err=True)
            echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
            sys.exit(1)
        if resolved_scope_id is None:
            typer.echo(f"failed to resolve folder {folder_path!r}: not found", err=True)
            sys.exit(1)
        base_scope_id = resolved_scope_id
        target_label = folder_path
    else:
        assert scope_id is not None
        try:
            _ = Folder.get_folder_path(cfg.user_id, cfg.company_id, scope_id)
        except Exception as exc:
            typer.echo(f"failed to resolve scope {scope_id!r}: {exc}", err=True)
            echo_credential_debug_if_auth_failure(cfg, exc, label="kb rm")
            sys.exit(1)
        base_scope_id = scope_id
        target_label = scope_id

    if files:
        _rm_files(
            cfg,
            base_scope_id,
            target_label,
            list(files),
            dry_run=dry_run,
            assume_yes=assume_yes,
        )
    else:
        _rm_folder(
            cfg,
            base_scope_id,
            target_label,
            recursive=recursive,
            dry_run=dry_run,
            assume_yes=assume_yes,
        )
