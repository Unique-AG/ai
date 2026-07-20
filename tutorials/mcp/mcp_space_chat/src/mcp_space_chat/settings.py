"""mcp_space_chat-specific settings (beyond unique_mcp ServerSettings)."""

from __future__ import annotations

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.util.find_env_file import find_env_file


class McpSpaceChatSettings(BaseSettings):
    """Settings for the Space Chat MCP server.

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

    frontend_base_url: HttpUrl = Field(
        description=(
            "Unique web app origin used to build the embedded chat iframe URL "
            "(e.g. https://next.qa.unique.app). Required: the chat window UI "
            "iframes {frontend}/chat/embed/{chatId}."
        ),
    )

    def frontend_base_url_str(self) -> str:
        return str(self.frontend_base_url).rstrip("/")

    def frontend_origin(self) -> str:
        """Origin (scheme://host[:port]) of the frontend for CSP frameDomains."""
        url = self.frontend_base_url
        origin = f"{url.scheme}://{url.host}"
        if url.port is not None and url.port not in (80, 443):
            origin += f":{url.port}"
        return origin
