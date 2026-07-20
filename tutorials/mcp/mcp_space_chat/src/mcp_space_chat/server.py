import logging
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from fastmcp.server.providers import FileSystemProvider
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_space_chat.routes import get_custom_routes_provider
from mcp_space_chat.settings import McpSpaceChatSettings
from mcp_space_chat.ui_resource import (
    CHAT_WINDOW_URI,
    HELLO_WORLD_URI,
    load_chat_window_html,
    load_hello_world_html,
)
from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.auth.zitadel.scopes import ZITADEL_DEFAULT_MCP_SCOPES
from unique_mcp.settings import ServerSettings

SERVER_INSTRUCTIONS = (
    "This server lets you delegate work to Unique spaces (specialized "
    "sub-agents) and can also render MCP Apps HTML. Workflow: 0) optional "
    "show_hello_world to verify the host displays HTML (560×360); "
    "1) list_spaces to discover available spaces; 2) ask_space to send a "
    "prompt — the user sees the live chat in an embedded window; "
    "3) get_space_answer only later if you need the final answer text. "
    "Pass the chatId from ask_space to follow-up calls to continue the same "
    "conversation."
)


def register_chat_window_resource(
    mcp: FastMCP, chat_settings: McpSpaceChatSettings
) -> None:
    """Register the MCP Apps chat window resource.

    The wrapper HTML mounts a nested iframe with the real Unique chat embed,
    so the frontend origin must be declared in ``csp.frameDomains`` — hosts
    build the sandbox CSP (``frame-src``) from this declaration.
    """

    @mcp.resource(
        CHAT_WINDOW_URI,
        name="space_chat_window",
        description="Live Unique space chat window (embeds the chat frontend).",
        mime_type="text/html;profile=mcp-app",
        app=AppConfig(
            csp=ResourceCSP(frame_domains=[chat_settings.frontend_origin()]),
            prefers_border=False,
        ),
    )
    def chat_window() -> str:
        return load_chat_window_html()


def register_hello_world_resource(mcp: FastMCP) -> None:
    """Register a no-iframe Hello World MCP Apps resource for smoke tests."""

    @mcp.resource(
        HELLO_WORLD_URI,
        name="hello_world_panel",
        description=(
            "Dummy animated Hello World HTML (560×360) to verify MCP Apps "
            "rendering without nesting the Unique chat iframe."
        ),
        mime_type="text/html;profile=mcp-app",
        app=AppConfig(prefers_border=True),
    )
    def hello_world() -> str:
        return load_hello_world_html()


def main() -> None:
    """Main entry point for the Space Chat MCP server."""

    logging.getLogger("mcp_space_chat").setLevel(logging.DEBUG)

    server_settings = ServerSettings()
    chat_settings = McpSpaceChatSettings()  # type: ignore[call-arg]

    oidc_proxy = create_zitadel_oidc_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(),  # type: ignore[call-arg]
        # Zitadel often issues opaque (non-JWT) access tokens even when the app
        # is configured for JWT. Verify the OIDC id_token instead so the
        # token-swap after /token succeeds; otherwise every /mcp call returns
        # invalid_token despite a successful login.
        verify_id_token=True,
    )
    # OIDCProxy does not advertise scopes by default; without this, DCR rejects
    # openid/profile and clients fail authorize (invalid_scope → invalid_token).
    oidc_proxy.update_default_scopes(list(ZITADEL_DEFAULT_MCP_SCOPES))

    tools_provider = FileSystemProvider(Path(__file__).parent / "tools")

    mcp = FastMCP(
        "Unique Space Chat",
        instructions=SERVER_INSTRUCTIONS,
        auth=oidc_proxy,
        providers=[tools_provider],
    )

    register_chat_window_resource(mcp, chat_settings)
    register_hello_world_resource(mcp)

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

    # FastMCP 3.4+ HostOriginGuardMiddleware:
    # - Host: only localhost is allowed when binding to 0.0.0.0 unless we
    #   advertise the public hostname (Azure Host: *.azurewebsites.net).
    # - Origin: behind TLS-terminating proxies the ASGI scheme is often http
    #   while the browser sends Origin: https://… — same-origin checks fail
    #   unless we explicitly allow the public HTTPS origin (and Zitadel for
    #   the OAuth redirect into /consent).
    public_url = str(server_settings.base_url).rstrip("/")
    public_host = server_settings.base_url.host
    zitadel = ZitadelOIDCProxySettings()  # type: ignore[call-arg]
    zitadel_origin = str(zitadel.base_url).rstrip("/")

    allowed_hosts = [h for h in {public_host, "localhost", "127.0.0.1"} if h]
    allowed_origins = [
        o
        for o in {
            public_url,
            f"https://{public_host}" if public_host else None,
            zitadel_origin,
            "http://localhost:8765",
            "http://127.0.0.1:8765",
            "http://localhost:8004",
            "http://127.0.0.1:8004",
        }
        if o
    ]

    mcp.run(
        transport=server_settings.transport_scheme,
        host=server_settings.local_base_url.host,
        port=server_settings.local_base_url.port,
        log_level="debug",
        middleware=middleware,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


if __name__ == "__main__":
    main()
