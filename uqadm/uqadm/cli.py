"""Click entry point for ``uqadm``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from uqadm import __version__
from uqadm.env import MissingSlotEnvFileError, config_for_slot
from uqadm.space_diff import cmd_diff as cmd_space_diff
from uqadm.space_export import cmd_export as cmd_space_export
from uqadm.space_list import cmd_list
from uqadm.space_migrate import cmd_migrate


class UqadmMainGroup(click.Group):
    """Catch missing slot env files and exit with instructions (no traceback)."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except MissingSlotEnvFileError as exc:
            click.echo(str(exc), err=True)
            ctx.exit(2)


@click.group(cls=UqadmMainGroup)
@click.version_option(version=__version__, prog_name="uqadm")
@click.option(
    "--cwd",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Directory for per-slot env files (.{slot}.env or {slot}.env; default: cwd).",
)
@click.pass_context
def main(ctx: click.Context, cwd: Path | None) -> None:
    """Unique admin CLI — space list & migrate (uses same UNIQUE_* env as unique-cli)."""
    state: dict[str, Path | None] = ctx.ensure_object(dict)
    state["cwd"] = cwd


@main.group()
def space() -> None:
    """Space administration."""


@space.command("list")
@click.argument("slot", metavar="SLOT")
@click.option(
    "--name",
    "name_filter",
    default=None,
    help="Case-insensitive partial filter on space name (passed to API).",
)
@click.option("--json", "as_json", is_flag=True, help="Print JSON instead of a table.")
@click.pass_context
def space_list(
    ctx: click.Context,
    slot: str,
    name_filter: str | None,
    as_json: bool,
) -> None:
    """List spaces for credentials in ``.{SLOT}.env`` or ``{SLOT}.env``."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cfg = config_for_slot(slot, cwd=cwd)
    cmd_list(cfg, name_filter=name_filter, as_json=as_json)


@space.command("export")
@click.argument(
    "spec",
    metavar="SPEC",
    required=True,
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    default=None,
    help=(
        "Write snapshot to this file; suffix must be .json, .yaml, or .yml "
        "(format follows extension). Omit for JSON on stdout."
    ),
)
@click.pass_context
def space_export(
    ctx: click.Context,
    spec: str,
    output: Path | None,
) -> None:
    """Export one space (``Space.get_space``): JSON on stdout, or JSON/YAML to -o by extension."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cmd_space_export(spec, output=output, cwd=cwd)


@space.command("diff")
@click.option(
    "--a",
    "spec_a",
    required=True,
    metavar="SPEC",
    help="First space endpoint (``slot:space_id`` or ``slot:URL``).",
)
@click.option(
    "--b",
    "spec_b",
    required=True,
    metavar="SPEC",
    help="Second space endpoint (same forms as ``--a``).",
)
@click.option(
    "--ignore-timestamps",
    is_flag=True,
    help="Remove createdAt/updatedAt recursively before comparing.",
)
@click.pass_context
def space_diff(
    ctx: click.Context,
    spec_a: str,
    spec_b: str,
    ignore_timestamps: bool,
) -> None:
    """Unified diff of two spaces (canonical JSON per side). Exit 1 if they differ."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cmd_space_diff(
        spec_a,
        spec_b,
        ignore_timestamps=ignore_timestamps,
        cwd=cwd,
    )


@space.command("migrate")
@click.option(
    "--source",
    required=True,
    help="Source endpoint: ``slot:space_id`` or ``slot:https://.../space/<id>``.",
)
@click.option(
    "--destination",
    required=True,
    help="Destination: ``slot`` or ``slot:`` for create; ``slot:space_id`` to update.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print actions without calling create/update/access APIs.",
)
@click.option(
    "--with-knowledge",
    is_flag=True,
    help="Reserved for same-environment extended migration (currently informational only).",
)
@click.pass_context
def space_migrate(
    ctx: click.Context,
    source: str,
    destination: str,
    dry_run: bool,
    with_knowledge: bool,
) -> None:
    """Clone assistant configuration from source space to destination (create or update)."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cmd_migrate(
        source,
        destination,
        dry_run=dry_run,
        with_knowledge=with_knowledge,
        cwd=cwd,
    )
