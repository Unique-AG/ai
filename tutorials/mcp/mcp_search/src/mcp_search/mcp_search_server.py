from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_search.routes import get_custom_routes_provider
from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.settings import ServerSettings


def main() -> None:
    """Main entry point for the MCP Search server."""

    server_settings = ServerSettings()

    oidc_proxy = create_zitadel_oidc_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(),  # type: ignore[call-arg]
    )

    tools_provider = FileSystemProvider(Path(__file__).parent / "tools")

    mcp = FastMCP(
        "Knowledge Base Search 🚀", auth=oidc_proxy, providers=[tools_provider]
    )

    mcp.mount(get_custom_routes_provider())

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    mcp.run(
        transport=server_settings.transport_scheme,
        host=server_settings.local_base_url.host,
        port=server_settings.local_base_url.port,
        log_level="debug",
        middleware=middleware,
    )


if __name__ == "__main__":
    main()
