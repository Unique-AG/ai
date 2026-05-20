"""Shared SDK setup for ``examples/basics`` scripts."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from unique_sdk.cli.config import Config, load_config

_BASICS_DIR = Path(__file__).resolve().parent
_PACKAGE_ROOT = _BASICS_DIR.parents[
    1
]  # ``unique_sdk/`` project root (``pyproject.toml``)

# Alternate env names → names ``load_config`` reads (first match wins per target).
_ENV_ALIASES: tuple[tuple[str, str], ...] = (
    ("API_KEY", "UNIQUE_API_KEY"),
    ("UNIQUE_APP_KEY", "UNIQUE_API_KEY"),
    ("APP_ID", "UNIQUE_APP_ID"),
    ("USER_ID", "UNIQUE_USER_ID"),
    ("UNIQUE_AUTH_USER_ID", "UNIQUE_USER_ID"),
    ("COMPANY_ID", "UNIQUE_COMPANY_ID"),
    ("UNIQUE_AUTH_COMPANY_ID", "UNIQUE_COMPANY_ID"),
    ("API_BASE", "UNIQUE_API_BASE"),
    ("UNIQUE_API_BASE_URL", "UNIQUE_API_BASE"),
    ("UNIQUE_API_VERSION", "UNIQUE_API_VERSION"),
)


def _default_env_file() -> Path:
    """Prefer ``examples/basics/.env``, then project-root ``.env``."""
    local = _BASICS_DIR / ".env"
    if local.exists():
        return local
    return _PACKAGE_ROOT / ".env"


def _apply_env_aliases() -> None:
    for legacy, canonical in _ENV_ALIASES:
        if os.environ.get(canonical):
            continue
        value = os.environ.get(legacy)
        if value:
            os.environ[canonical] = value


def _normalize_api_base() -> None:
    """Bare gateway host → ``/unique-api`` (Briefings and public OpenAPI surface)."""
    raw = os.environ.get("UNIQUE_API_BASE", "").strip().strip("'\"")
    if not raw:
        return
    base = raw.rstrip("/")
    if "/unique-api" in base:
        os.environ.setdefault("UNIQUE_API_VERSION", "2026-03-01")
        return
    if "/public/" in base:
        return
    # e.g. https://gateway.unique.app → https://gateway.unique.app/unique-api
    if "gateway" in base and base.count("/") <= 2:
        os.environ["UNIQUE_API_BASE"] = f"{base}/unique-api"
        os.environ.setdefault("UNIQUE_API_VERSION", "2026-03-01")


def configure_sdk(env_file: Path | None = None) -> Config:
    """Load ``.env``, map legacy env names, and wire ``unique_sdk`` via ``load_config``.

    Args:
        env_file: Path to a dotenv file. Defaults to ``examples/basics/.env`` when present.

    Returns:
        Resolved :class:`~unique_sdk.cli.config.Config` (also sets ``unique_sdk`` globals).
    """
    path = env_file if env_file is not None else _default_env_file()
    if path.exists():
        load_dotenv(path)
    _apply_env_aliases()
    _normalize_api_base()
    config = load_config()
    import unique_sdk

    base = (os.environ.get("UNIQUE_API_BASE") or unique_sdk.api_base).rstrip("/")
    if "/unique-api" in base:
        unique_sdk.api_version = os.environ.get("UNIQUE_API_VERSION", "2026-03-01")
    return config
