"""Interactive confirmation prompt for bulk sweeps."""

from __future__ import annotations

from typing import Literal

import typer

Decision = Literal["yes", "no", "all", "quit"]

_HELP_TEXT = "Please answer y (yes), n (no), a (yes to all), or q (quit)."


def confirm_each(prompt: str) -> Decision:
    """Ask ``prompt`` and return yes / no / all (yes to everything) / quit."""
    while True:
        answer = typer.prompt(f"{prompt} [y/n/a/q]", default="n").strip().lower()
        if answer in ("y", "yes"):
            return "yes"
        if answer in ("n", "no"):
            return "no"
        if answer in ("a", "all"):
            return "all"
        if answer in ("q", "quit"):
            return "quit"
        typer.echo(_HELP_TEXT)
