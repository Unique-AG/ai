"""Knowledge base (folder) administration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Optional

import typer

from uqadm.core.cli_auth import load_config_or_exit, resolve_slot_or_exit
from uqadm.kb.access import cmd_access_grant
from uqadm.kb.download import cmd_download
from uqadm.kb.ingestion import cmd_ingestion_set
from uqadm.kb.mkdir import cmd_mkdir
from uqadm.kb.rm import cmd_rm
from uqadm.kb.sync import cmd_sync

kb_app = typer.Typer(
    name="kb",
    help=(
        "Knowledge-base folder administration: create paths (Folder.create_paths), "
        "sync/download files, remove folders/files (Folder.delete, Content.delete), "
        "grant group access (Folder.add_access), set ingestion "
        "(Folder.update_ingestion_config)."
    ),
    no_args_is_help=True,
)

_ACCESS_SUBHELP = (
    "Grant READ/WRITE to groups on folder scopes. Wraps Folder.add_access; "
    "by default applies to subfolders (see grant --no-subfolders)."
)
_INGESTION_SUBHELP = (
    "Load folder ingestion settings from a JSON/YAML file. Wraps "
    "Folder.update_ingestion_config (not the same shape as space settings.ingestionConfig)."
)

_SLOT_HELP = (
    "Credential slot: loads .{SLOT}.env or {SLOT}.env. "
    "Omit to use the configured default (see `uqadm env set-default`). "
    "Ignored when UQADM_AUTH_FROM_ENV is set — credentials are read from the "
    "process environment and no slot file is used."
)


def _get_cwd(ctx: typer.Context) -> Path | None:
    return (ctx.obj or {}).get("cwd")


@kb_app.command("mkdir", short_help="Create folder paths in the knowledge base.")
def kb_mkdir(
    ctx: typer.Context,
    paths: Annotated[
        Optional[list[str]],
        typer.Argument(
            help="Folder paths to create (repeat or combine with --paths-file).",
        ),
    ] = None,
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    paths_file: Annotated[
        Optional[Path],
        typer.Option(
            "--paths-file",
            help="Text file: one path per line; ``#`` starts a comment.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    path_option: Annotated[
        Optional[list[str]],
        typer.Option(
            "--path",
            help="Folder path (repeatable).",
        ),
    ] = None,
    parent_scope_id: Annotated[
        Optional[str],
        typer.Option(
            "--parent-scope-id",
            help="Create ``relativePaths`` under this parent scope instead of absolute ``paths``.",
        ),
    ] = None,
    inherit_access: Annotated[
        bool,
        typer.Option(
            "--inherit-access/--no-inherit-access",
            help="Whether new folders inherit parent access (default: inherit).",
        ),
    ] = True,
) -> None:
    """Create folder paths in the tenant KB.

    Uses ``Folder.create_paths``. Pass absolute paths, or ``--parent-scope-id`` with
    relative segments. Combine positional paths, ``--path``, and/or ``--paths-file``.

    Examples:

      uqadm kb mkdir /Dept/HR /Dept/Legal
      uqadm kb mkdir --path /Reports/2024 --path /Reports/2025 --slot qa
      uqadm kb mkdir --paths-file folders.txt
      uqadm kb mkdir rel/sub --parent-scope-id scope_parent123
      uqadm kb mkdir /Private --no-inherit-access
    """
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, _get_cwd(ctx))
    combined = (paths or []) + (path_option or [])
    cmd_mkdir(
        cfg,
        extra_paths=combined,
        paths_file=paths_file,
        parent_scope_id=parent_scope_id,
        inherit_access=inherit_access,
    )


@kb_app.command("sync", short_help="Sync a local folder into a KB scope.")
def kb_sync(
    ctx: typer.Context,
    local_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            readable=True,
            help="Local folder whose contents are synced into the KB scope.",
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    folder_path: Annotated[
        Optional[str],
        typer.Option(
            "--folder-path",
            help="Target KB folder path (mutually exclusive with --scope-id).",
        ),
    ] = None,
    scope_id: Annotated[
        Optional[str],
        typer.Option(
            "--scope-id",
            help="Target folder scope id (mutually exclusive with --folder-path).",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-r",
            help="Recurse into subdirectories, mirroring them as child KB folders.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show planned uploads without writing anything.",
        ),
    ] = False,
    no_version: Annotated[
        bool,
        typer.Option(
            "--no-version",
            help="Upload without archiving prior blobs.",
        ),
    ] = False,
) -> None:
    """Upload the contents of LOCAL_DIR into a knowledge-base folder.

    Files already present (matched by filename) are replaced; new files are
    created. Files present in the target scope but missing locally are left
    untouched; ``sync`` never deletes remote files. Requires exactly one of
    ``--folder-path`` or ``--scope-id`` to name the target scope. Without
    ``--recursive`` only top-level files are synced; with it, subdirectories are
    recreated as child folders under the target.

    By default, replaced files archive prior blobs (restorable via
    ``unique-cli versions`` / ``restore-version``). Pass ``--no-version`` to
    skip archiving (legacy overwrite behavior). Content ids are unchanged on
    replace (upsert by filename key).

    Examples:

      uqadm kb sync ./docs --folder-path /Dept/HR
      uqadm kb sync ./docs --folder-path /Dept/HR -r --dry-run
      uqadm kb sync ./docs --scope-id scope_abc -r --slot qa
      uqadm kb sync ./docs --scope-id scope_abc --no-version
    """
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, _get_cwd(ctx))
    cmd_sync(
        cfg,
        local_dir=local_dir,
        folder_path=folder_path,
        scope_id=scope_id,
        recursive=recursive,
        dry_run=dry_run,
        versioning=not no_version,
    )


@kb_app.command(
    "download", short_help="Download KB scope contents into a local folder."
)
def kb_download(
    ctx: typer.Context,
    local_dir: Annotated[
        Path,
        typer.Argument(
            file_okay=False,
            writable=True,
            help="Local folder where KB files are written (created if missing).",
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    folder_path: Annotated[
        Optional[str],
        typer.Option(
            "--folder-path",
            help="Source KB folder path (mutually exclusive with --scope-id).",
        ),
    ] = None,
    scope_id: Annotated[
        Optional[str],
        typer.Option(
            "--scope-id",
            help="Source folder scope id (mutually exclusive with --folder-path).",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-r",
            help="Recurse into subfolders, mirroring them as local subdirectories.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show planned downloads without writing anything.",
        ),
    ] = False,
) -> None:
    """Download files from a knowledge-base folder into LOCAL_DIR.

    Requires exactly one of ``--folder-path`` or ``--scope-id`` to name the
    source scope. Without ``--recursive`` only top-level files are downloaded;
    with it, subfolders are recreated as child directories under LOCAL_DIR.

    Examples:

      uqadm kb download ./out --folder-path /Dept/HR
      uqadm kb download ./out --folder-path /Dept/HR -r --dry-run
      uqadm kb download ./out --scope-id scope_abc -r --slot qa
    """
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, _get_cwd(ctx))
    cmd_download(
        cfg,
        local_dir=local_dir,
        folder_path=folder_path,
        scope_id=scope_id,
        recursive=recursive,
        dry_run=dry_run,
    )


@kb_app.command("rm", short_help="Delete KB folders or individual files.")
def kb_rm(
    ctx: typer.Context,
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    folder_path: Annotated[
        Optional[str],
        typer.Option(
            "--folder-path",
            help="Target KB folder path (mutually exclusive with --scope-id).",
        ),
    ] = None,
    scope_id: Annotated[
        Optional[str],
        typer.Option(
            "--scope-id",
            help="Target folder scope id (mutually exclusive with --folder-path).",
        ),
    ] = None,
    file: Annotated[
        Optional[list[str]],
        typer.Option(
            "--file",
            help="Delete only this file (matched by key) in the scope; repeatable.",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-r",
            help="Delete a non-empty folder and everything under it.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be deleted without deleting anything.",
        ),
    ] = False,
    assume_yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip the interactive confirmation prompt.",
        ),
    ] = False,
) -> None:
    """Delete a knowledge-base folder or specific files within it.

    Requires exactly one of ``--folder-path`` or ``--scope-id`` to name the
    target scope. With one or more ``--file`` options only those files are
    deleted (Content.delete); otherwise the whole folder is deleted
    (Folder.delete). Deleting a non-empty folder requires ``--recursive``.
    Unless ``--yes`` is given you are prompted to confirm; ``--dry-run`` prints
    the plan without deleting.

    Examples:

      uqadm kb rm --folder-path /Dept/HR --file old.pdf
      uqadm kb rm --scope-id scope_abc -r --dry-run
      uqadm kb rm --scope-id scope_abc -r --slot qa -y
    """
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, _get_cwd(ctx))
    cmd_rm(
        cfg,
        folder_path=folder_path,
        scope_id=scope_id,
        files=tuple(file or []),
        recursive=recursive,
        dry_run=dry_run,
        assume_yes=assume_yes,
    )


access_app = typer.Typer(
    help=_ACCESS_SUBHELP,
    short_help="Grant group access on KB folders (Folder.add_access).",
    no_args_is_help=True,
)


@access_app.command(
    "grant",
    short_help="Grant group READ/WRITE on a folder (subfolders included by default).",
)
def kb_access_grant(
    ctx: typer.Context,
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    folder_path: Annotated[
        Optional[str],
        typer.Option(
            "--folder-path",
            help="Folder path (mutually exclusive with --scope-id).",
        ),
    ] = None,
    scope_id: Annotated[
        Optional[str],
        typer.Option(
            "--scope-id",
            help="Folder scope id (mutually exclusive with --folder-path).",
        ),
    ] = None,
    group: Annotated[
        Optional[list[str]],
        typer.Option(
            "--group",
            help="Group id (repeatable).",
        ),
    ] = None,
    permission: Annotated[
        Literal["READ", "WRITE"],
        typer.Option(
            "--permission",
            help="Group access level for the folder scope(s).",
            show_default=True,
        ),
    ] = "READ",
    no_subfolders: Annotated[
        bool,
        typer.Option(
            "--no-subfolders",
            help="Do not apply to descendant folders (default: apply to subfolders).",
        ),
    ] = False,
) -> None:
    """Grant one or more groups access to a folder scope.

    Requires exactly one of ``--folder-path`` or ``--scope-id``. Repeating ``--group``
    adds multiple groups in one call. Unless ``--no-subfolders`` is set, the API
    applies the same access to descendant folders (``applyToSubScopes``).

    Examples:

      uqadm kb access grant --folder-path /Dept/HR --group grp_1
      uqadm kb access grant --folder-path /Dept/HR --group grp_1 --group grp_2 --permission WRITE
      uqadm kb access grant --scope-id scope_abc --group grp_1 --slot qa
      uqadm kb access grant --folder-path /Dept/HR --group grp_1 --no-subfolders
    """
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, _get_cwd(ctx))
    cmd_access_grant(
        cfg,
        folder_path=folder_path,
        scope_id=scope_id,
        group_ids=tuple(group or []),
        permission=permission,
        apply_to_subfolders=not no_subfolders,
    )


kb_app.add_typer(access_app, name="access")

ingestion_app = typer.Typer(
    help=_INGESTION_SUBHELP,
    short_help="Folder ingestion JSON/YAML (Folder.update_ingestion_config).",
    no_args_is_help=True,
)


@ingestion_app.command(
    "set",
    short_help="Apply ingestion config from CONFIG_FILE to a folder scope.",
)
def kb_ingestion_set(
    ctx: typer.Context,
    config_file: Annotated[
        Path,
        typer.Argument(
            metavar="CONFIG_FILE",
            help=(
                "JSON or YAML file; root must be a mapping. Sent as folder "
                "ingestionConfig (Folder.update_ingestion_config; differs from "
                "``uqadm space ingestion-set``)."
            ),
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    folder_path: Annotated[
        Optional[str],
        typer.Option(
            "--folder-path", help="Folder path (mutually exclusive with --scope-id)."
        ),
    ] = None,
    scope_id: Annotated[
        Optional[str],
        typer.Option(
            "--scope-id",
            help="Folder scope id (mutually exclusive with --folder-path).",
        ),
    ] = None,
    no_subfolders: Annotated[
        bool,
        typer.Option(
            "--no-subfolders",
            help="Do not apply to descendant folders (default: apply to subfolders).",
        ),
    ] = False,
) -> None:
    """Patch folder ingestion using a JSON or YAML mapping file.

    The file root must be an object; it is sent as ``ingestionConfig``. Requires
    exactly one of ``--folder-path`` or ``--scope-id``. By default the patch
    applies to subfolders unless ``--no-subfolders`` is set.

    For assistant-level chat ingestion, use ``uqadm space ingestion-set`` instead.

    Examples:

      uqadm kb ingestion set ./folder-ingest.json --folder-path /Dept/HR
      uqadm kb ingestion set ./ingest.yaml --scope-id scope_abc --slot qa
      uqadm kb ingestion set ./ingest.json --folder-path /Dept/HR --no-subfolders
    """
    resolved_slot = resolve_slot_or_exit(slot)
    cfg = load_config_or_exit(resolved_slot, _get_cwd(ctx))
    cmd_ingestion_set(
        cfg,
        config_path=config_file,
        folder_path=folder_path,
        scope_id=scope_id,
        apply_to_subfolders=not no_subfolders,
    )


kb_app.add_typer(ingestion_app, name="ingestion")
