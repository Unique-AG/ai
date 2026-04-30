"""Load per-slot `.{{slot}}.env` files and apply SDK CLI config."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from unique_sdk.cli.config import Config, load_config

UNIQUE_ENV_KEYS = (
    "UNIQUE_USER_ID",
    "UNIQUE_COMPANY_ID",
    "UNIQUE_API_KEY",
    "UNIQUE_APP_ID",
    "UNIQUE_API_BASE",
)


def env_file_for_slot(slot: str, cwd: Path | None = None) -> Path:
    """Resolve ``.{slot}.env`` under ``cwd`` (default: process cwd)."""
    base = cwd or Path.cwd()
    return base / f".{slot}.env"


def clear_unique_env_vars() -> None:
    """Remove UNIQUE_* keys so switching slots does not leak prior values."""
    for key in UNIQUE_ENV_KEYS:
        os.environ.pop(key, None)


def load_slot(slot: str, cwd: Path | None = None) -> Path:
    """Load ``.{slot}.env`` into ``os.environ`` (override=True), return path."""
    path = env_file_for_slot(slot, cwd)
    if not path.is_file():
        raise FileNotFoundError(f"Missing env file: {path}")
    clear_unique_env_vars()
    _: bool = load_dotenv(path, override=True)
    return path


def config_for_slot(slot: str, cwd: Path | None = None) -> Config:
    """Load slot env file and run the same wiring as ``unique-cli``."""
    load_slot(slot, cwd)
    return load_config()


def normalize_api_base(url: str) -> str:
    """Normalize API base URL for same-environment comparison."""
    return url.rstrip("/")
