"""Shared CLI helpers: resolve a slot / load its config, or exit cleanly.

These wrap :func:`resolve_slot` and :func:`config_for_slot` so every command
turns the same credential errors into a guidance message on stderr and exit
code ``2`` (instead of a Python traceback), in one place.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from unique_sdk.cli.config import Config

from uqadm.core.env import (
    MissingEnvCredentialsError,
    MissingSlotEnvFileError,
    config_for_slot,
)
from uqadm.core.slot import MissingDefaultSlotError, resolve_slot

# These helpers exit via ``sys.exit`` (SystemExit) rather than ``typer.Exit``.
# ``typer.Exit`` subclasses ``RuntimeError``, so a broad ``except Exception``
# around a call site (e.g. ``space diff``) would swallow it and mask the exit
# code; ``SystemExit`` is a ``BaseException`` and passes through cleanly.


def resolve_slot_or_exit(slot: str | None) -> str:
    """Resolve the active slot, or print guidance and exit with code 2."""
    try:
        return resolve_slot(slot)
    except MissingDefaultSlotError as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)


def load_config_or_exit(slot: str, cwd: Path | None) -> Config:
    """Load the slot's SDK config, or print guidance and exit with code 2."""
    try:
        return config_for_slot(slot, cwd=cwd)
    except (MissingSlotEnvFileError, MissingEnvCredentialsError) as exc:
        typer.echo(str(exc), err=True)
        sys.exit(2)
