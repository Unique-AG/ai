"""Typer entry point for ``uqadm``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from uqadm import __version__
from uqadm.chat import chat_app
from uqadm.core.env import MissingSlotEnvFileError
from uqadm.env import env_app
from uqadm.install import install_command
from uqadm.kb import kb_app
from uqadm.space import space_app

app = typer.Typer(
    name="uqadm",
    help="Unique admin CLI — space and knowledge-base admin (uses same UNIQUE_* env as unique-cli).",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(space_app, name="space")
app.add_typer(kb_app, name="kb")
app.add_typer(chat_app, name="chat")
app.add_typer(env_app, name="env")
app.command("install")(install_command)


@app.callback(invoke_without_command=True)
def root_callback(
    ctx: typer.Context,
    cwd: Annotated[
        Optional[Path],
        typer.Option(
            "--cwd",
            help=(
                "Directory for per-slot env files (.{slot}.env or {slot}.env). "
                "Defaults to ~/.uqadm/envs/ then process cwd."
            ),
            file_okay=False,
            dir_okay=True,
        ),
    ] = None,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    if version:
        typer.echo(f"uqadm {__version__}")
        raise typer.Exit()
    ctx.ensure_object(dict)
    ctx.obj["cwd"] = cwd
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def main() -> None:
    try:
        app()
    except MissingSlotEnvFileError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)
