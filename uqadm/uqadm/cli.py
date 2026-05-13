"""Click entry point for ``uqadm``."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Literal, cast, override

import click
from click.formatting import HelpFormatter

from uqadm import __version__
from uqadm.env import MissingSlotEnvFileError, config_for_slot
from uqadm.space_delete import cmd_delete as cmd_space_delete
from uqadm.space_diff import cmd_diff as cmd_space_diff
from uqadm.space_export import cmd_export as cmd_space_export
from uqadm.space_list import cmd_list
from uqadm.space_migrate import cmd_migrate
from uqadm.space_upsert import cmd_upsert as cmd_space_upsert

# Click paragraph marker ``\\b`` keeps example lines from being rewrapped (see ``click.formatting.wrap_text``).
_HELP_EPILOG_MAIN = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space list --slot qa
      uqadm --cwd /path/to/secrets space export --source "qa:space_abc" -o backup.json
    """
)

_HELP_EPILOG_SPACE = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space list --slot qa --name Report
      uqadm space export --source "qa:space_abc" -o snapshot.yaml
      uqadm space migrate --source "1:space_src" --destination "2:"
    """
)

_HELP_EPILOG_LIST = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space list --slot qa
      uqadm space list --slot prod --name Report
      uqadm --cwd ~/secrets space list --slot 1 --json
    """
)

_HELP_EPILOG_EXPORT = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space export --source "qa:space_abc"
      uqadm space export --source "qa:https://host/app/space/space_xyz" -o backup.json
      uqadm --cwd ~/secrets space export --source "1:space_abc" -o snapshot.yaml
    """
)

_HELP_EPILOG_UPSERT = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space upsert --destination "2:" --file ./new-space.yaml
      uqadm space upsert --destination "qa:space_dst" -f ./edited.json --dry-run
    """
)

_HELP_EPILOG_DIFF = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space diff --source "1:space_a" --destination "1:space_b"
      uqadm space diff --source "qa:space_x" --destination "prod:space_y" --format side-by-side
      uqadm space diff --source "qa:x" --destination "prod:y" --strict
    """
)

_HELP_EPILOG_MIGRATE = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space migrate --source "1:space_src" --destination "2:"
      uqadm space migrate --source "qa:space_x" --destination "prod:space_y" --dry-run
    """
)

_HELP_EPILOG_DELETE = inspect.cleandoc(
    """
    \b
    Examples:
      uqadm space delete --source "qa:space_old" --dry-run
      uqadm space delete --source "prod:space_x" -y
    """
)


def _root_context(ctx: click.Context) -> click.Context:
    """Return the root invocation context for ``uqadm`` by walking ``parent``."""
    root = ctx
    while root.parent is not None:
        root = root.parent
    return root


class ShowsRootGlobalOptionsMixin:
    """Prepend root-level flags (--cwd, --version) on nested command/group help."""

    def format_options(self, ctx: click.Context, formatter: HelpFormatter) -> None:
        root_ctx = _root_context(ctx)
        if ctx.command is not root_ctx.command:
            rows: list[tuple[str, str]] = []
            for param in root_ctx.command.params:
                # click.HelpOption existed only in 8.1.8 and was removed in 8.2.0;
                # match the help option by name instead.
                if param.name == "help":
                    continue
                if not isinstance(param, click.Option):
                    continue
                record = param.get_help_record(root_ctx)
                if record is not None:
                    rows.append(record)
            if rows:
                with formatter.section("Global options (uqadm)"):
                    formatter.write_dl(rows)
        cast(click.Command, super()).format_options(ctx, formatter)


class UqadmNestedCommand(ShowsRootGlobalOptionsMixin, click.Command):
    """Leaf command that documents inherited ``uqadm`` flags in ``--help``."""


class UqadmNestedGroup(ShowsRootGlobalOptionsMixin, click.Group):
    """Group whose ``--help`` lists inherited ``uqadm`` flags; subcommands use :class:`UqadmNestedCommand`."""

    command_class: type[click.Command] | None = UqadmNestedCommand


class UqadmMainGroup(click.Group):
    """Catch missing slot env files and exit with instructions (no traceback)."""

    @override
    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except MissingSlotEnvFileError as exc:
            click.echo(str(exc), err=True)
            ctx.exit(2)


@click.group(cls=UqadmMainGroup, epilog=_HELP_EPILOG_MAIN)
@click.version_option(version=__version__, prog_name="uqadm")
@click.option(
    "--cwd",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Directory for per-slot env files (.{slot}.env or {slot}.env; default: cwd).",
)
@click.pass_context
def main(ctx: click.Context, cwd: Path | None) -> None:
    """Unique admin CLI — space admin (uses same UNIQUE_* env as unique-cli)."""
    state: dict[str, Path | None] = ctx.ensure_object(dict)
    state["cwd"] = cwd


@main.group(cls=UqadmNestedGroup, epilog=_HELP_EPILOG_SPACE)
def space() -> None:
    """Space administration."""


@space.command(
    "list",
    epilog=_HELP_EPILOG_LIST,
    short_help="List spaces (--slot selects credential env file).",
)
@click.option(
    "--slot",
    "slot",
    required=True,
    metavar="SLOT",
    help=(
        "Credential slot: loads ``.{SLOT}.env`` or ``{SLOT}.env`` (under global ``--cwd`` if set)."
    ),
)
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
    """List spaces using credentials from ``.{SLOT}.env`` or ``{SLOT}.env`` for ``--slot``."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cfg = config_for_slot(slot, cwd=cwd)
    cmd_list(cfg, name_filter=name_filter, as_json=as_json)


@space.command(
    "export",
    short_help=(
        "Export space snapshot (--source SPEC; JSON on stdout or -o FILE .json/.yaml/.yml)."
    ),
    epilog=_HELP_EPILOG_EXPORT,
)
@click.option(
    "--source",
    "spec",
    required=True,
    metavar="SPEC",
    help=(
        "Space endpoint: ``slot:space_id`` or ``slot:https://.../space/<id>`` "
        "(same forms as ``space migrate --source``)."
    ),
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
    """Export one space (``Space.get_space``): JSON on stdout, or JSON/YAML to ``-o`` by extension."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cmd_space_export(spec, output=output, cwd=cwd)


@space.command("upsert", epilog=_HELP_EPILOG_UPSERT)
@click.option(
    "--destination",
    "spec",
    required=True,
    metavar="SPEC",
    help=(
        "Space endpoint to create or update: ``slot`` or ``slot:`` to create; "
        "``slot:space_id`` or ``slot:https://...`` to update (same forms as "
        "``space migrate --destination``)."
    ),
)
@click.option(
    "-f",
    "--file",
    "file",
    type=click.Path(path_type=Path, dir_okay=False, exists=True, readable=True),
    required=True,
    help="Local snapshot path (.json, .yaml, or .yml).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print actions without calling create/update/access APIs.",
)
@click.pass_context
def space_upsert(
    ctx: click.Context,
    spec: str,
    file: Path,
    dry_run: bool,
) -> None:
    """Create or update a space from ``--file`` snapshot (.json/.yaml/.yml); ``--destination`` is the target (same as migrate)."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cmd_space_upsert(spec, file, dry_run=dry_run, cwd=cwd)


@space.command("diff", epilog=_HELP_EPILOG_DIFF)
@click.option(
    "--source",
    "spec_a",
    required=True,
    metavar="SPEC",
    help="First space endpoint (``slot:space_id`` or ``slot:URL``; same forms as ``space migrate --source``).",
)
@click.option(
    "--destination",
    "spec_b",
    required=True,
    metavar="SPEC",
    help=(
        "Second space endpoint (same forms as ``--source``). "
        "Order only affects diff headers, not comparison semantics."
    ),
)
@click.option(
    "--strict",
    is_flag=True,
    help=(
        "Compare raw payloads (keep ids, timestamps, companyId, etc.). "
        "Default mode strips ephemeral fields so the diff focuses on config content."
    ),
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["unified", "side-by-side"], case_sensitive=False),
    default="unified",
    help=(
        "unified: two-column line diff with inline word highlights when stdout is a TTY; "
        "otherwise classic unified diff text. "
        "side-by-side: two syntax-highlighted JSON panels (wide terminal recommended)."
    ),
)
@click.pass_context
def space_diff(
    ctx: click.Context,
    spec_a: str,
    spec_b: str,
    strict: bool,
    output_format: str,
) -> None:
    """Compare two spaces (normalized by default); exit 1 if they still differ after normalization."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    fmt: Literal["unified", "side-by-side"] = (
        "side-by-side" if output_format.lower() == "side-by-side" else "unified"
    )
    cmd_space_diff(
        spec_a,
        spec_b,
        strict=strict,
        output_format=fmt,
        cwd=cwd,
    )


@space.command("migrate", epilog=_HELP_EPILOG_MIGRATE)
@click.option(
    "--source",
    required=True,
    metavar="SPEC",
    help="Source endpoint: ``slot:space_id`` or ``slot:https://.../space/<id>``.",
)
@click.option(
    "--destination",
    required=True,
    metavar="SPEC",
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


@space.command("delete", epilog=_HELP_EPILOG_DELETE)
@click.option(
    "--source",
    "spec",
    required=True,
    metavar="SPEC",
    help=(
        "Space to delete: ``slot:space_id`` or ``slot:https://...`` with extractable id "
        "(same forms as ``space migrate --source`` / ``space export --source``)."
    ),
)
@click.option("-y", "--yes", is_flag=True, help="Skip the confirmation prompt.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Fetch the space and print what would be deleted without calling delete_space.",
)
@click.pass_context
def space_delete(
    ctx: click.Context,
    spec: str,
    yes: bool,
    dry_run: bool,
) -> None:
    """Delete one space (``Space.delete_space``); ``--source`` is the space endpoint."""
    state = ctx.ensure_object(dict)
    cwd: Path | None = state.get("cwd")
    cmd_space_delete(spec, yes=yes, dry_run=dry_run, cwd=cwd)
