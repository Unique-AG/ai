"""Framework settings shared by per-dataset MCP servers.

Each dataset server passes explicit Excel and SQLite paths when it constructs
`AppSettings`. Pydantic-settings ranks constructor arguments above environment
variables, so anything a dataset passes explicitly cannot be overridden from the
environment or a `.env` file — only the fields a dataset leaves unset (the
transport host and port, header detection) read from the environment.
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
