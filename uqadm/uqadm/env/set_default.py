"""Set the default credential slot."""

from __future__ import annotations

import typer

from uqadm.core.config_file import set_default_slot
from uqadm.core.env import MissingSlotEnvFileError, env_file_for_slot


def cmd_env_set_default(slot: str) -> None:
    """Validate that ``slot`` exists, then write it as the default in config.toml."""
    try:
        env_path = env_file_for_slot(slot)
    except MissingSlotEnvFileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)

    set_default_slot(slot)
    typer.echo(f"Default slot set to {slot!r} (env file: {env_path}).")
