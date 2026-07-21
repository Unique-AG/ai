"""mcp_search-specific server settings (extends unique_mcp ServerSettings)."""

from pydantic import Field, HttpUrl

from unique_mcp.settings import ServerSettings


class McpSearchServerSettings(ServerSettings):
    """ServerSettings plus the deep-link origin used by this server's tools.

    Subclass rather than a unique_mcp field: knowledge-upload deep links are
    an mcp_search concern, not shared server config. Same env prefix, so the
    variable stays ``UNIQUE_MCP_FRONTEND_BASE_URL``.
    """

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
