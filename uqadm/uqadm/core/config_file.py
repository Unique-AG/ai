"""Read and write ``~/.uqadm/config.toml`` (default slot and other settings)."""

from __future__ import annotations

import tomllib
from typing import Any

import tomli_w

from uqadm.core.paths import config_path


def load_config() -> dict[str, Any]:
    """Return the parsed config, or an empty dict if the file does not exist."""
    path = config_path()
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def save_config(data: dict[str, Any]) -> None:
    """Persist ``data`` to ``config.toml``, creating parent dirs as needed."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tomli_w.dumps(data).encode())


def get_default_slot() -> str | None:
    """Return the configured default slot name, or ``None`` if unset."""
    return load_config().get("default_slot")


def set_default_slot(slot: str) -> None:
    """Persist ``slot`` as the default in ``config.toml``."""
    data = load_config()
    data["default_slot"] = slot
    save_config(data)
