"""Canonical filesystem paths for uqadm's home directory."""

from __future__ import annotations

import os
from pathlib import Path


def uqadm_home() -> Path:
    """Return the uqadm home directory.

    Resolved from the ``UQADM_HOME`` environment variable when set; otherwise
    ``~/.uqadm``.
    """
    raw = os.environ.get("UQADM_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".uqadm"


def envs_dir() -> Path:
    """Return ``<uqadm_home>/envs`` (the standard slot env file directory)."""
    return uqadm_home() / "envs"


def config_path() -> Path:
    """Return ``<uqadm_home>/config.toml``."""
    return uqadm_home() / "config.toml"
