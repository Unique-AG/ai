"""Resolve the active credential slot from CLI input or configured default."""

from __future__ import annotations

from uqadm.core.config_file import get_default_slot
from uqadm.core.env import auth_from_env_enabled


class MissingDefaultSlotError(RuntimeError):
    """Raised when no slot is provided and no default is configured."""


def resolve_slot(cli_slot: str | None) -> str:
    """Return ``cli_slot`` when given, else fall back to the configured default.

    When ``UQADM_AUTH_FROM_ENV`` is set, credentials come from the environment
    rather than a slot file, so ``"env"`` is returned as a display label when no
    explicit slot is given.

    Raises:
        MissingDefaultSlotError: If neither ``cli_slot`` nor a configured
            default slot is available (and env-auth is not enabled).
    """
    if cli_slot:
        return cli_slot
    if auth_from_env_enabled():
        return "env"
    default = get_default_slot()
    if default:
        return default
    raise MissingDefaultSlotError(
        "No slot specified and no default slot is configured.\n\n"
        "Either pass --slot <name> explicitly, or run:\n"
        "  uqadm env set-default <slot>\n\n"
        "To see available slots:\n"
        "  uqadm env list\n\n"
        "To create a new slot:\n"
        "  uqadm env create <slot>"
    )
