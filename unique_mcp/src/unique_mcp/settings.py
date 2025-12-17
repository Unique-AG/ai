from fastmcp.server.server import Transport
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.util.find_env_file import find_env_file


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(filenames=["unique_mcp.env", ".env"], required=False),
        env_prefix="UNIQUE_MCP_",
        extra="allow",
        frozen=True,
    )

    public_base_url: HttpUrl | None = Field(
        default=None, description="The public base URL of the MCP server."
    )

    local_base_url: HttpUrl = Field(
        default=HttpUrl("http://localhost:8003"),
        description="The private base URL of the MCP server.",
    )

    @property
    def base_url(self) -> HttpUrl:
        return self.public_base_url or self.local_base_url

    @property
    def transport_scheme(self) -> Transport:
        url = self.public_base_url or self.local_base_url

        match url.scheme:
            case "http":
                return "http"
            case "https":
                return "http"
            case "sse":
                return "sse"
            case "streamable-http":
                return "streamable-http"
            case _:
                raise ValueError(f"Invalid scheme: {url.scheme}")
