"""Space administration sub-app."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Literal, Optional

import typer

from uqadm.core.env import MissingSlotEnvFileError, config_for_slot
from uqadm.core.slot import MissingDefaultSlotError, resolve_slot
from uqadm.space.access_grant import cmd_space_access_grant
from uqadm.space.delete import cmd_delete
from uqadm.space.diff import cmd_diff
from uqadm.space.export import cmd_export
from uqadm.space.ingestion_set import cmd_space_ingestion_set
from uqadm.space.list import cmd_list
from uqadm.space.migrate import cmd_migrate
from uqadm.space.model_replace import cmd_model_replace
from uqadm.space.upsert import cmd_upsert

space_app = typer.Typer(
    name="space",
    help="Space administration.",
    no_args_is_help=True,
)

_SLOT_HELP = (
    "Credential slot: loads .{SLOT}.env or {SLOT}.env. "
    "Omit to use the configured default (see `uqadm env set-default`)."
)


def _get_cwd(ctx: typer.Context) -> Path | None:
    return (ctx.obj or {}).get("cwd")


def _resolve(slot: str | None) -> str:
    try:
        return resolve_slot(slot)
    except MissingDefaultSlotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)


def _load_cfg(slot: str, cwd: Path | None):  # type: ignore[no-untyped-def]
    """Call config_for_slot, converting MissingSlotEnvFileError to a clean exit."""
    try:
        return config_for_slot(slot, cwd=cwd)
    except MissingSlotEnvFileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)


@space_app.command("list", short_help="List spaces in a slot.")
def space_list(
    ctx: typer.Context,
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name", help="Case-insensitive partial filter on space name."),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print JSON instead of a table.")
    ] = False,
) -> None:
    """List spaces using credentials from the resolved slot env file."""
    cwd = _get_cwd(ctx)
    resolved_slot = _resolve(slot)
    cfg = _load_cfg(resolved_slot, cwd)
    cmd_list(cfg, name_filter=name_filter, as_json=as_json, slot=resolved_slot)


@space_app.command(
    "export",
    short_help="Export space snapshot (JSON on stdout or -o FILE .json/.yaml/.yml).",
)
def space_export(
    ctx: typer.Context,
    space_id: Annotated[
        str,
        typer.Argument(
            metavar="SPACE_ID",
            help="Space id or URL to export (e.g. assistant_abc or https://host/.../space/assistant_abc).",
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o",
            "--output",
            help="Write snapshot to file; suffix must be .json, .yaml, or .yml.",
        ),
    ] = None,
) -> None:
    """Export one space: JSON on stdout, or JSON/YAML to -o by extension."""
    resolved_slot = _resolve(slot)
    cfg = _load_cfg(resolved_slot, _get_cwd(ctx))
    cmd_export(space_id, cfg=cfg, output=output)


@space_app.command(
    "upsert", short_help="Create or update a space from a snapshot file."
)
def space_upsert(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Option(
            "-f",
            "--file",
            help="Local snapshot path (.json, .yaml, or .yml).",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    target: Annotated[
        Optional[str],
        typer.Option(
            "--target",
            metavar="SPACE_ID",
            help=(
                "Space id or URL to update. "
                "Omit to create a new space on the resolved slot."
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Print actions without calling create/update APIs."
        ),
    ] = False,
) -> None:
    """Create or update a space from a snapshot file.

    Omit --target to create a new space. Provide --target SPACE_ID to update
    an existing space. --slot selects the credential slot (default slot if omitted).
    """
    from uqadm.core.endpoint import EndpointParseError, parse_bare_endpoint

    resolved_slot = _resolve(slot)
    target_space_id: str | None = None
    if target is not None:
        try:
            target_space_id = parse_bare_endpoint(target)
        except EndpointParseError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(2)
    cmd_upsert(
        file,
        resolved_slot,
        target_space_id=target_space_id,
        dry_run=dry_run,
        cwd=_get_cwd(ctx),
    )


@space_app.command("diff", short_help="Compare two spaces.")
def space_diff(
    ctx: typer.Context,
    spec_a: Annotated[
        str,
        typer.Option(
            "--source",
            metavar="SPEC",
            help="First space endpoint (slot:space_id or slot:URL).",
        ),
    ],
    spec_b: Annotated[
        str,
        typer.Option(
            "--destination",
            metavar="SPEC",
            help="Second space endpoint (slot:space_id or slot:URL).",
        ),
    ],
    strict: Annotated[
        bool,
        typer.Option(
            "--strict",
            help="Compare raw payloads (keep ids, timestamps, etc.).",
        ),
    ] = False,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="unified or side-by-side.",
            show_default=True,
        ),
    ] = "unified",
) -> None:
    """Compare two spaces (normalized by default); exit 1 if they differ."""
    cmd_diff(
        spec_a,
        spec_b,
        strict=strict,
        output_format=output_format,
        cwd=_get_cwd(ctx),
    )


@space_app.command(
    "migrate", short_help="Clone space config from source to destination."
)
def space_migrate(
    ctx: typer.Context,
    source: Annotated[
        str,
        typer.Option(
            "--source",
            metavar="SPEC",
            help="Source endpoint: slot:space_id or slot:https://.../space/<id>.",
        ),
    ],
    destination: Annotated[
        str,
        typer.Option(
            "--destination",
            metavar="SPEC",
            help="Destination: slot or slot: for create; slot:space_id to update.",
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Print actions without calling create/update APIs."
        ),
    ] = False,
    with_knowledge: Annotated[
        bool,
        typer.Option(
            "--with-knowledge",
            help="Reserved for same-environment extended migration (currently informational only).",
        ),
    ] = False,
) -> None:
    """Clone assistant configuration from source space to destination."""
    cmd_migrate(
        source,
        destination,
        dry_run=dry_run,
        with_knowledge=with_knowledge,
        cwd=_get_cwd(ctx),
    )


@space_app.command(
    "model-replace",
    short_help="Replace a language model across a space, snapshot file, or all spaces.",
)
def space_model_replace(
    ctx: typer.Context,
    from_model: Annotated[
        str,
        typer.Option(
            "--from-model",
            help="Model name currently in the configuration that should be replaced.",
        ),
    ],
    to_model: Annotated[
        str,
        typer.Option(
            "--to-model",
            help=(
                "Replacement model: a model name, or a path to a .json/.yaml/.yml "
                "file with language-model info (must include 'name')."
            ),
        ),
    ],
    space_id: Annotated[
        Optional[str],
        typer.Argument(
            metavar="[SPACE_ID]",
            help=(
                "Space id or URL to rewrite (mutually exclusive with --file and --all)."
            ),
        ),
    ] = None,
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    file: Annotated[
        Optional[Path],
        typer.Option(
            "-f",
            "--file",
            help="Local snapshot (.json/.yaml/.yml) to rewrite instead of a live space.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    all_spaces: Annotated[
        bool,
        typer.Option(
            "--all",
            help="Iterate every space in the slot, prompting per matching space.",
        ),
    ] = False,
    name_filter: Annotated[
        Optional[str],
        typer.Option(
            "--name",
            help="With --all: case-insensitive partial filter on space name.",
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "-o",
            "--output",
            help=(
                "Write the rewritten snapshot to this .json/.yaml/.yml file "
                "instead of updating the platform (stdout for --file without -o)."
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print matched paths and planned updates without writing anything.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="With --all: apply without prompting."),
    ] = False,
) -> None:
    """Replace one language model with another across a space configuration.

    Rewrites every model-bearing key (``languageModel``, ``fallbackModel``,
    ``hallucinationModel``, nested tool/module configs, ``switchableLanguageModels``
    entries, …) whose value equals ``--from-model``. Prompt text and non-model
    fields are never touched.

    ``--to-model`` takes a model name, or a path to a .json/.yaml/.yml file
    holding language-model info: a name is written as a plain string, a file is
    written as the full mapping it contains.

    Input is exactly one of: a SPACE_ID (live space), ``--file`` (local
    snapshot), or ``--all`` (interactive sweep over every space in the slot,
    prompting y/n/a/q per matching space). With ``-o`` the rewritten snapshot
    is written to a file and no API write happens; otherwise the space is
    updated in place with a minimal payload. Only ``--all`` prompts: a single
    SPACE_ID applies immediately, so use ``--dry-run`` first to preview.
    Note: a single-space run does not follow links into sub-agent spaces;
    ``--all`` covers them because it iterates every space in the slot.

    Examples:

      uqadm space model-replace asst_abc --from-model AZURE_GPT_4o_2024_0806 --to-model AZURE_GPT_5_2025_0807 --dry-run
      uqadm space model-replace asst_abc --from-model AZURE_GPT_4o_2024_0806 --to-model AZURE_GPT_5_2025_0807 -o migrated.yaml
      uqadm space model-replace -f backup.yaml --from-model OLD --to-model ./new-model.yaml -o backup.migrated.yaml
      uqadm space model-replace --all --slot prod --from-model OLD --to-model NEW
    """
    from uqadm.core.endpoint import EndpointParseError, parse_bare_endpoint

    parsed_space_id: str | None = None
    if space_id is not None:
        try:
            parsed_space_id = parse_bare_endpoint(space_id)
        except EndpointParseError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(2)

    cfg = None
    if parsed_space_id is not None or all_spaces:
        resolved_slot = _resolve(slot)
        cfg = _load_cfg(resolved_slot, _get_cwd(ctx))

    cmd_model_replace(
        cfg,
        space_id=parsed_space_id,
        file_path=file,
        sweep_all=all_spaces,
        name_filter=name_filter,
        from_model=from_model,
        to_model=to_model,
        output=output,
        dry_run=dry_run,
        assume_yes=yes,
    )


@space_app.command(
    "access-grant",
    short_help="Add user/group space access (merged with existing ACL).",
)
def space_access_grant(
    ctx: typer.Context,
    space_id: Annotated[
        str,
        typer.Argument(
            metavar="SPACE_ID",
            help="Space id or URL (e.g. assistant_abc or https://host/.../space/assistant_abc).",
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    group: Annotated[
        Optional[List[str]],
        typer.Option("--group", help="Group id (repeatable)."),
    ] = None,
    user: Annotated[
        Optional[List[str]],
        typer.Option("--user", help="User id (repeatable)."),
    ] = None,
    access_type: Annotated[
        Literal["USE", "MANAGE", "UPLOAD"],
        typer.Option(
            "--type",
            help="Access level for every ``--group`` / ``--user`` on this call.",
            show_default=True,
        ),
    ] = "USE",
) -> None:
    """Add USE / MANAGE / UPLOAD entries for users and/or groups.

    Each run posts to ``Space.add_space_access``; entries are merged with the existing
    ACL rather than replacing it. Repeat ``--group`` / ``--user`` for multiple principals.

    Examples:

      uqadm space access-grant asst_abc --group grp_1
      uqadm space access-grant asst_abc --group grp_1 --group grp_2
      uqadm space access-grant asst_abc --user user_1 --type MANAGE --slot qa
    """
    from uqadm.core.endpoint import EndpointParseError, parse_bare_endpoint

    resolved_slot = _resolve(slot)
    cfg = _load_cfg(resolved_slot, _get_cwd(ctx))
    try:
        sid = parse_bare_endpoint(space_id)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)
    cmd_space_access_grant(
        cfg,
        space_id=sid,
        group_ids=tuple(group or []),
        user_ids=tuple(user or []),
        access_type=access_type,
    )


@space_app.command(
    "ingestion-set",
    short_help="Merge settings.ingestionConfig from a JSON/YAML file.",
)
def space_ingestion_set(
    ctx: typer.Context,
    space_id: Annotated[
        str,
        typer.Argument(
            metavar="SPACE_ID",
            help="Space id or URL to patch.",
        ),
    ],
    config_file: Annotated[
        Path,
        typer.Argument(
            metavar="CONFIG_FILE",
            exists=True,
            dir_okay=False,
            readable=True,
            help=(
                "JSON or YAML file whose root is a mapping; becomes "
                "settings.ingestionConfig (assistant chat/file ingestion, not folder API)."
            ),
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show which settings keys would be patched."),
    ] = False,
) -> None:
    """Merge ``settings.ingestionConfig`` from a JSON/YAML file.

    Fetches the space, shallow-merges top-level ``settings``, and sets
    ``ingestionConfig`` to the file contents (replacing the previous object).
    Use ``--dry-run`` to print which settings keys would be sent. For KB folder
    ingestion, use ``uqadm kb ingestion set``.

    Examples:

      uqadm space ingestion-set asst_abc ./ingestion.json
      uqadm space ingestion-set asst_abc ./ingestion.yaml --slot prod
      uqadm space ingestion-set asst_abc ./ingestion.json --dry-run
    """
    from uqadm.core.endpoint import EndpointParseError, parse_bare_endpoint

    resolved_slot = _resolve(slot)
    cfg = _load_cfg(resolved_slot, _get_cwd(ctx))
    try:
        sid = parse_bare_endpoint(space_id)
    except EndpointParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)
    cmd_space_ingestion_set(
        cfg,
        space_id=sid,
        config_path=config_file,
        dry_run=dry_run,
    )


@space_app.command("delete", short_help="Delete a space.")
def space_delete(
    ctx: typer.Context,
    space_id: Annotated[
        str,
        typer.Argument(
            metavar="SPACE_ID",
            help="Space id or URL to delete (e.g. assistant_abc or https://host/.../space/assistant_abc).",
        ),
    ],
    slot: Annotated[Optional[str], typer.Option("--slot", help=_SLOT_HELP)] = None,
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Skip the confirmation prompt."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Fetch the space and print what would be deleted."
        ),
    ] = False,
) -> None:
    """Delete one space using the default slot or --slot."""
    resolved_slot = _resolve(slot)
    cfg = _load_cfg(resolved_slot, _get_cwd(ctx))
    cmd_delete(space_id, cfg=cfg, yes=yes, dry_run=dry_run)
