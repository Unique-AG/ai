"""List available credential slots."""

from __future__ import annotations

import typer

from uqadm.core.config_file import get_default_slot
from uqadm.core.paths import envs_dir


def cmd_env_list() -> None:
    """List slot env files in ``~/.uqadm/envs/``."""
    directory = envs_dir()
    default_slot = get_default_slot()

    if not directory.is_dir():
        typer.echo("No slots found. Run `uqadm env create <slot>` to create one.")
        return

    slots: list[str] = []
    for f in sorted(directory.iterdir()):
        name = f.name
        if name.startswith(".") and name.endswith(".env") and f.is_file():
            slots.append(name[1:-4])  # strip leading dot and .env suffix
        elif name.endswith(".env") and not name.startswith(".") and f.is_file():
            slots.append(name[:-4])  # strip .env suffix

    if not slots:
        typer.echo("No slots found. Run `uqadm env create <slot>` to create one.")
        return

    for slot in slots:
        marker = " *" if slot == default_slot else ""
        typer.echo(f"  {slot}{marker}")

    if default_slot:
        typer.echo(f"\n* = default slot ({default_slot!r})")
    else:
        typer.echo("\nNo default slot configured. Run `uqadm env set-default <slot>`.")
