"""mcp_search-specific server settings (extends unique_mcp ServerSettings)."""

from pydantic import Field, HttpUrl

from unique_mcp.settings import ServerSettings


class McpSearchServerSettings(ServerSettings):
    """ServerSettings plus optional frontend origin for knowledge-upload deep links."""

    frontend_base_url: HttpUrl | None = Field(
        default=None,
        description=(
            "Unique web app origin used to build clickable knowledge-upload "
            "deep links, e.g. https://<identifier>.unique.app. When unset, "
            "references fall back to unique://content/{id}."
        ),
    )

    def frontend_base_url_str(self) -> str | None:
        if self.frontend_base_url is None:
            return None
        return str(self.frontend_base_url).rstrip("/")
