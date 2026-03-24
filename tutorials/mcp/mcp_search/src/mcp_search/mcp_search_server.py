from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_search.routes import MCPBaseRoutes
from mcp_search.tools import UniqueKnowledgeBaseTools
from unique_mcp.server import create_mcp_server


def main() -> None:
    """Main entry point for the MCP Search server."""
    bundle = create_mcp_server("Knowledge Base Search 🚀")

    custom_middleware = [
        Middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    UniqueKnowledgeBaseTools(bundle.context_provider).register(mcp=bundle.mcp)
    MCPBaseRoutes().register(mcp=bundle.mcp)

    bundle.mcp.run(
        transport=bundle.server_settings.transport_scheme,
        host=bundle.server_settings.local_base_url.host,
        port=bundle.server_settings.local_base_url.port,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
