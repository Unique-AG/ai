"""Delete a credential slot env file."""

from __future__ import annotations

import typer

from uqadm.core.config_file import get_default_slot, load_config, save_config
from uqadm.core.env import MissingSlotEnvFileError, env_file_for_slot


def cmd_env_delete(slot: str, *, yes: bool) -> None:
    """Remove the env file for ``slot`` (with confirmation)."""
    try:
        env_path = env_file_for_slot(slot)
    except MissingSlotEnvFileError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2)

    if not yes:
        confirmed = typer.confirm(f"Delete slot {slot!r} ({env_path})?", default=False)
        if not confirmed:
            typer.echo("Aborted.")
            return

    env_path.unlink()
    typer.echo(f"Deleted {env_path}.")

    if get_default_slot() == slot:
        data = load_config()
        data.pop("default_slot", None)
        save_config(data)
        typer.echo(
            f"Note: {slot!r} was the default slot. "
            "Run `uqadm env set-default <slot>` to configure a new default."
        )
