"""Env management sub-app — create, list, show, set-default, delete credential slots."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from uqadm.env.create import cmd_env_create
from uqadm.env.delete import cmd_env_delete
from uqadm.env.list import cmd_env_list
from uqadm.env.set_default import cmd_env_set_default
from uqadm.env.show import cmd_env_show

env_app = typer.Typer(
    name="env",
    help="Manage credential slots (~/.uqadm/envs/).",
    no_args_is_help=True,
)

_SLOT_META = typer.Argument(
    metavar="SLOT", help="Credential slot name (e.g. qa, prod)."
)


def _get_cwd(ctx: typer.Context) -> Path | None:
    return (ctx.obj or {}).get("cwd")


@env_app.command("create", short_help="Create a new credential slot.")
def env_create(
    slot: Annotated[str, _SLOT_META],
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing slot file."),
    ] = False,
    set_default: Annotated[
        bool,
        typer.Option(
            "--set-default", help="Set this slot as the default after creating."
        ),
    ] = False,
    non_interactive: Annotated[
        bool,
        typer.Option(
            "--non-interactive",
            help="Skip prompts; use --user-id / --company-id flags.",
        ),
    ] = False,
    user_id: Annotated[
        Optional[str],
        typer.Option("--user-id", help="UNIQUE_USER_ID value."),
    ] = None,
    company_id: Annotated[
        Optional[str],
        typer.Option("--company-id", help="UNIQUE_COMPANY_ID value."),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", help="UNIQUE_API_KEY value (optional)."),
    ] = None,
    app_id: Annotated[
        Optional[str],
        typer.Option("--app-id", help="UNIQUE_APP_ID value (optional)."),
    ] = None,
    api_base: Annotated[
        Optional[str],
        typer.Option("--api-base", help="UNIQUE_API_BASE value (optional)."),
    ] = None,
) -> None:
    """Interactively create a new credential slot in ~/.uqadm/envs/."""
    cmd_env_create(
        slot,
        force=force,
        set_default=set_default,
        non_interactive=non_interactive,
        user_id=user_id,
        company_id=company_id,
        api_key=api_key,
        app_id=app_id,
        api_base=api_base,
    )


@env_app.command("list", short_help="List available credential slots.")
def env_list() -> None:
    """List all slot env files in ~/.uqadm/envs/ with the default marked by *."""
    cmd_env_list()


@env_app.command("show", short_help="Show resolved credentials for a slot.")
def env_show(
    ctx: typer.Context,
    slot: Annotated[
        Optional[str],
        typer.Argument(
            metavar="SLOT", help="Slot to inspect (default: configured default slot)."
        ),
    ] = None,
) -> None:
    """Print resolved credential values (API key redacted)."""
    cmd_env_show(slot, cwd=_get_cwd(ctx))


@env_app.command("set-default", short_help="Set the default credential slot.")
def env_set_default(slot: Annotated[str, _SLOT_META]) -> None:
    """Write slot as the default in ~/.uqadm/config.toml after validating it exists."""
    cmd_env_set_default(slot)


@env_app.command("delete", short_help="Delete a credential slot.")
def env_delete(
    slot: Annotated[str, _SLOT_META],
    yes: Annotated[
        bool,
        typer.Option("-y", "--yes", help="Skip the confirmation prompt."),
    ] = False,
) -> None:
    """Remove the env file for SLOT (with confirmation unless -y)."""
    cmd_env_delete(slot, yes=yes)
