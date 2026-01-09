from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_template.routes import MCPBaseRoutes
from mcp_template.tools import TemplateTools

# Uncomment this if you want to use the zitadel oauth proxy
# from unique_mcp.auth.zitadel.oauth_proxy import (
#     ZitadelOAuthProxySettings,
#     create_zitadel_oauth_proxy,
# )
from unique_mcp.settings import ServerSettings
from unique_toolkit.app.unique_settings import UniqueSettings


def main() -> None:
    """
    Main entry point for the MCP template server.
    This function sets up and runs the FastMCP server with all necessary
    configuration including OAuth, CORS, tools, and routes.
    """
    # This will automatically init the SDK and give you access to all relevant settings
    _UNIQUE_SETTINGS = UniqueSettings.from_env_auto_with_sdk_init()

    server_settings = ServerSettings()  # type: ignore

    print("BASE URL: ", server_settings.base_url.encoded_string())
    print("LOCAL BASE URL: ", server_settings.local_base_url.encoded_string())

    # You can use any oauth proxy you want, we use the idp from the unique platform here
    # zitadel_oauth_proxy = create_zitadel_oauth_proxy(
    #    mcp_server_base_url=server_settings.base_url.encoded_string(),
    #    zitadel_oauth_proxy_settings=ZitadelOAuthProxySettings(),
    # )

    custom_middleware = [
        Middleware(
            CORSMiddleware,
            allow_credentials=True,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    mcp = FastMCP(
        name="MCP Template 🚀",
    )

    template_tools = TemplateTools(
        unique_settings=_UNIQUE_SETTINGS,
    )
    template_tools.register(mcp=mcp)

    mcp_base_routes = MCPBaseRoutes()
    mcp_base_routes.register(mcp=mcp)

    # mcp.auth = zitadel_oauth_proxy

    mcp.run(
        transport=server_settings.transport_scheme,
        host=server_settings.local_base_url.host,
        port=server_settings.local_base_url.port,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
