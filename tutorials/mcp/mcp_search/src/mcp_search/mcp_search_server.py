from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_search.routes import MCPBaseRoutes
from mcp_search.tools import UniqueKnowledgeBaseTools
from unique_mcp.auth.zitadel.oauth_proxy import (
    ZitadelOAuthProxySettings,
    create_zitadel_oauth_proxy,
)
from unique_mcp.settings import ServerSettings


def main() -> None:
    """Main entry point for the MCP Search server."""

    server_settings = ServerSettings()
    zitadel_settings = ZitadelOAuthProxySettings()

    oauth_proxy = create_zitadel_oauth_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oauth_proxy_settings=zitadel_settings,
    )

    mcp = FastMCP("Knowledge Base Search 🚀", auth=oauth_proxy)

    custom_middleware = [
        Middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    UniqueKnowledgeBaseTools().register(mcp=mcp)
    MCPBaseRoutes().register(mcp=mcp)

    mcp.auth = None

    mcp.run(
        transport=server_settings.transport_scheme,
        host=server_settings.local_base_url.host,
        port=server_settings.local_base_url.port,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
