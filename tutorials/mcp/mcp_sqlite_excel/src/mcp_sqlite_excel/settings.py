"""Application configuration via pydantic-settings (Excel/SQLite paths only).

Zitadel OAuth and bind URL come from ``unique_mcp``:

- ``ZitadelOIDCProxySettings`` → ``zitadel.env`` / ``ZITADEL_*``
- ``ServerSettings`` → ``unique_mcp.env`` / ``UNIQUE_MCP_*``
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class AppSettings(BaseSettings):
    """Excel / SQLite paths and local-demo auth toggle."""

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
        description="When true, skip Zitadel OIDC (local demos only).",
    )
    excel_header_row: int | None = Field(
        default=None,
        ge=1,
        description=(
            "1-based Excel row to use as the header. When unset, the loader "
            "auto-detects the first wide text row (skips title/blank preamble)."
        ),
    )
    excel_min_header_cells: int = Field(
        default=3,
        ge=1,
        description=(
            "Minimum non-empty cells for auto-detected header rows. "
            "Keeps title-only / key-value sheets from being misread as tables."
        ),
    )


@lru_cache
def get_settings() -> AppSettings:
    """Return the cached application settings singleton."""
    return AppSettings()
