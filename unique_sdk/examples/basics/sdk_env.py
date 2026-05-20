"""Shared SDK setup for ``examples/basics`` scripts."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from unique_sdk.cli.config import Config, load_config

# Project root (``unique_sdk/`` with ``pyproject.toml`` and ``.env``).
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_FILE = _PACKAGE_ROOT / ".env"

# Legacy tutorial / custom-assistant names → CLI ``load_config`` expects UNIQUE_*.
_ENV_ALIASES: tuple[tuple[str, str], ...] = (
    ("API_KEY", "UNIQUE_API_KEY"),
    ("APP_ID", "UNIQUE_APP_ID"),
    ("USER_ID", "UNIQUE_USER_ID"),
    ("COMPANY_ID", "UNIQUE_COMPANY_ID"),
    ("API_BASE", "UNIQUE_API_BASE"),
)


def _apply_env_aliases() -> None:
    for legacy, canonical in _ENV_ALIASES:
        if os.environ.get(canonical):
            continue
        value = os.environ.get(legacy)
        if value:
            os.environ[canonical] = value


def configure_sdk(env_file: Path | None = None) -> Config:
    """Load ``.env``, map legacy env names, and wire ``unique_sdk`` via ``load_config``.

    Args:
        env_file: Path to a dotenv file. Defaults to ``unique_sdk/.env``.

    Returns:
        Resolved :class:`~unique_sdk.cli.config.Config` (also sets ``unique_sdk`` globals).
    """
    path = env_file if env_file is not None else _DEFAULT_ENV_FILE
    if path.exists():
        load_dotenv(path)
    _apply_env_aliases()
    return load_config()
