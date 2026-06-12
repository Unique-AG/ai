"""Sync a local folder into a knowledge-base scope."""

from __future__ import annotations

import glob
import mimetypes
import sys
from pathlib import Path

import typer
from unique_sdk import Content, Folder, InvalidRequestError
from unique_sdk.cli.config import Config
from unique_sdk.utils.file_io import upload_file

from uqadm.core.auth_debug import echo_credential_debug_if_auth_failure

_PAGE_SIZE = 100


def _collect_files(folder: Path, recursive: bool) -> list[Path]:
    if recursive:
        walker = (Path(p) for p in glob.glob(f"{folder}/**", recursive=True))
    else:
        walker = folder.iterdir()
    return sorted(p for p in walker if p.is_file())


def _join_folder_paths(left: str, right: str) -> str:
    """Join a relative subdirectory onto the base KB folder path."""
    return f"{left.rstrip('/')}/{right.lstrip('/')}"


def _resolve_scope(cfg: Config, folder_path: str, *, create: bool) -> str | None:
    """Resolve a folder path to its scope id, optionally creating it.

    With ``create`` (a real run) the folder is created if missing; any failure
    propagates so the caller can report it. Without ``create`` (a dry run) a
    missing folder is expected — the SDK raises ``ValueError`` rather than
    returning ``None`` for an unknown path, so we swallow that and return
    ``None`` to mean "no existing scope; treat its files as new". Other errors
    (auth, network) are not caught and still surface.
    """
    if create:
        return Folder.resolve_scope_id_from_folder_path_with_create(
            cfg.user_id, cfg.company_id, folder_path=folder_path
        )
    try:
        return Folder.resolve_scope_id_from_folder_path(
            cfg.user_id, cfg.company_id, folder_path=folder_path
        )
    except InvalidRequestError:  # Raised by the sdk if not found
        return None


def _remote_keys(cfg: Config, scope_id: str) -> set[str]:
    """Return the content keys already present in a folder scope."""
    keys: set[str] = set()
    skip = 0
    while True:
        page = Content.get_infos(
            cfg.user_id,
            cfg.company_id,
            parentId=scope_id,
            skip=skip,
            take=_PAGE_SIZE,
        )
        infos = page.get("contentInfos") or []
        keys.update(info["key"] for info in infos)
        skip += len(infos)
        if not infos or skip >= page.get("totalCount", 0):
            break
    return keys


def cmd_sync(
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

    # Reduce both --folder-path and --scope-id to a base folder path so the rest
    # of the command is path-based and identical for either entry point.
    if folder_path:
        base_path = folder_path
    else:
        assert scope_id is not None
        try:
            base_path = Folder.get_folder_path(cfg.user_id, cfg.company_id, scope_id)[
                "folderPath"
            ]
        except Exception as exc:
            typer.echo(f"failed to resolve scope {scope_id!r}: {exc}", err=True)
            echo_credential_debug_if_auth_failure(cfg, exc, label="kb sync")
            sys.exit(1)

    files = _collect_files(local_dir, recursive)
    if len(files) == 0:
        typer.echo("No files to sync.")
        return

    # Group files by their target folder path, relative to local_dir. An empty
    # relative parent means the base target folder itself.
    groups: dict[str, list[Path]] = {}
    for path in files:
        rel_parent = path.parent.relative_to(local_dir).as_posix()
        groups.setdefault("" if rel_parent == "." else rel_parent, []).append(path)

    counts = {"new": 0, "replaced": 0, "failed": 0}
    for rel_parent, paths in sorted(groups.items()):
        target_path = _join_folder_paths(base_path, rel_parent)
        try:
            target_scope = _resolve_scope(cfg, target_path, create=not dry_run)
        except Exception as exc:
            typer.echo(f"failed to resolve folder {target_path!r}: {exc}", err=True)
            echo_credential_debug_if_auth_failure(cfg, exc, label="kb sync")
            counts["failed"] += len(paths)
            continue

        existing = _remote_keys(cfg, target_scope) if target_scope else set()

        for path in paths:
            display = path.relative_to(local_dir).as_posix()
            mime, _ = mimetypes.guess_type(path.name)
            if mime is None:
                typer.echo(
                    f"failed: {display}: could not determine MIME type", err=True
                )
                counts["failed"] += 1
                continue
            action = "replaced" if path.name in existing else "new"
            if dry_run:
                typer.echo(f"[dry-run] {action}: {display}")
                counts[action] += 1
                continue
            try:
                upload_file(
                    cfg.user_id,
                    cfg.company_id,
                    str(path),
                    path.name,
                    mime,
                    scope_or_unique_path=target_scope,
                )
            except Exception as exc:
                typer.echo(f"failed: {display}: {exc}", err=True)
                echo_credential_debug_if_auth_failure(cfg, exc, label="kb sync")
                counts["failed"] += 1
                continue
            typer.echo(f"{action}: {display}")
            counts[action] += 1

    typer.echo(
        f"Done: {counts['new']} new, {counts['replaced']} replaced, "
        f"{counts['failed']} failed."
    )
    if counts["failed"]:
        sys.exit(1)
