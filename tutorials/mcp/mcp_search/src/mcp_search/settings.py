"""mcp_search-specific settings (beyond unique_mcp ServerSettings)."""

from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.util.find_env_file import find_env_file


class McpSearchSettings(BaseSettings):
    """Settings for the Knowledge Base Search MCP server.

    Env vars use the ``UNIQUE_`` prefix (shared with Unique API credentials in
    ``unique.env``), e.g. ``UNIQUE_FRONTEND_BASE_URL``.
    """

    model_config = SettingsConfigDict(
        env_file=find_env_file(
            filenames=["unique.env", "unique_mcp.env", ".env"], required=False
        ),
        env_prefix="UNIQUE_",
        extra="ignore",
        frozen=True,
    )

    frontend_base_url: HttpUrl | None = Field(
        default=None,
        description=(
            "Unique web app origin used to build clickable knowledge-upload "
            "deep links, e.g. https://next.qa.unique.app. When unset, "
            "references fall back to unique://content/{id}."
        ),
    )

    def frontend_base_url_str(self) -> str | None:
        if self.frontend_base_url is None:
            return None
        return str(self.frontend_base_url).rstrip("/")
