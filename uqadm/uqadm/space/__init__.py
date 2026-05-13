"""Space administration sub-app."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from uqadm.core.env import MissingSlotEnvFileError, config_for_slot
from uqadm.core.slot import MissingDefaultSlotError, resolve_slot
from uqadm.space.delete import cmd_delete
from uqadm.space.diff import cmd_diff
from uqadm.space.export import cmd_export
from uqadm.space.list import cmd_list
from uqadm.space.migrate import cmd_migrate
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
