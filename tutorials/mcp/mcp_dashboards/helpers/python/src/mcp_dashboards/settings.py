"""Framework settings shared by per-dataset MCP servers.

Each dataset server should pass Excel and SQLite paths only when the matching
environment variables are unset. Pydantic-settings ranks constructor arguments
above environment variables, so an explicit `excel_path=` / `sqlite_path=`
argument cannot be overridden by `EXCEL_PATH` / `SQLITE_PATH` — which is what
keeps datasets isolated locally, and why deploy must leave those kwargs off when
Azure supplies persisted paths.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Excel / SQLite paths and HTTP transport binding for one dataset."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    excel_path: Path = Field(
        description="Excel workbook used to seed this dataset's SQLite database."
    )
    sqlite_path: Path = Field(description="Per-dataset SQLite database file path.")
    host: str = Field(
        default="127.0.0.1",
        description="Address the streamable-http transport binds to.",
    )
    port: int = Field(
        default=8004,
        ge=1,
        le=65535,
        description="Port the streamable-http transport binds to.",
    )
    auth_disabled: bool = Field(
        default=False,
        description="When true, skip Zitadel OIDC (local demos only).",
    )
    excel_header_row: int | None = Field(
        default=None,
        ge=1,
        description="1-based Excel row to use as the header. When unset, the loader auto-detects it.",
    )
    excel_min_header_cells: int = Field(
        default=3,
        ge=1,
        description="Minimum non-empty cells for auto-detected header rows.",
    )
