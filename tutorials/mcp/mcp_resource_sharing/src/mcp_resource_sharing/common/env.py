"""Shared pydantic-settings wiring for the demo."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import SettingsConfigDict

# compose/.env — loaded by Docker Compose; also used when running MCP modules locally.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / "compose" / ".env"


def settings_config(*, env_prefix: str) -> SettingsConfigDict:
    """Return a SettingsConfigDict that reads the shared ``.env`` file."""
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )
