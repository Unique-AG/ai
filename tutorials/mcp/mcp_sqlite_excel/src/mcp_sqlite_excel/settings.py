"""Application configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class AppSettings(BaseSettings):
    """Runtime settings for the SQLite Excel MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    excel_path: Path = Field(
        default_factory=lambda: DEFAULT_DATA_DIR / "sample_portfolio.xlsx",
        description="Excel workbook used to seed SQLite.",
    )
    sqlite_path: Path = Field(
        default_factory=lambda: DEFAULT_DATA_DIR / "portfolio.db",
        description="SQLite database file path.",
    )
    auth_disabled: bool = Field(
        default=False,
        description="When true, run without Zitadel OAuth (local demos).",
    )
    port: int = Field(default=8004, ge=1, le=65535)
    host: str | None = Field(
        default=None,
        description="Bind host. Defaults to 127.0.0.1 when auth is disabled, else 0.0.0.0.",
    )
    base_url_env: str = Field(
        default="https://default.ngrok-free.app",
        description="Public base URL for the OAuth proxy.",
    )
    zitadel_url: str = Field(default="http://localhost:10116")
    upstream_client_id: str = Field(default="default_client_id")
    upstream_client_secret: str = Field(default="default_client_secret")

    @property
    def bind_host(self) -> str:
        if self.host is not None:
            return self.host
        # Containers / App Service need 0.0.0.0; local auth-disabled demos stay loopback.
        return "127.0.0.1" if self.auth_disabled else "0.0.0.0"


@lru_cache
def get_settings() -> AppSettings:
    """Return the cached application settings singleton."""
    return AppSettings()
