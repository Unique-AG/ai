from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_search.routes import get_custom_routes_provider
from unique_mcp.auth.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_mcp.settings import ServerSettings


def main() -> None:
    """Main entry point for the MCP Search server."""

    server_settings = ServerSettings()

    # TODO: Replace by OIDC Proxy
    zitadel_settings = ZitadelOAuthProxySettings()
    oauth_proxy = create_zitadel_oauth_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oauth_proxy_settings=zitadel_settings,
    )

    file_system_provider = FileSystemProvider(Path(__file__).parent)

    mcp = FastMCP(
        "Knowledge Base Search 🚀", auth=oauth_proxy, providers=[file_system_provider]
    )
    mcp.mount(get_custom_routes_provider())

    # TODO: Talk to Andreas why we need this
    # FastMcp recommends against it https://gofastmcp.com/integrations/fastapi#cors-middleware
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
