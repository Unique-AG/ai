import logging
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
from key_value.aio.stores.memory import MemoryStore
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from mcp_search.references import SERVER_CITATION_INSTRUCTIONS
from mcp_search.routes import get_custom_routes_provider
from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.settings import ServerSettings


def main() -> None:
    """Main entry point for the MCP Search server."""

    logging.getLogger("mcp_search").setLevel(logging.DEBUG)

    server_settings = ServerSettings()

    oidc_proxy = create_zitadel_oidc_proxy(
        # In-memory: dev-only, loses every session on restart and doesn't work
        # across replicas. Never deploy this tutorial multi-pod as-is — use a
        # shared, encrypted-at-rest AsyncKeyValue backend for real deployments.
        client_storage=MemoryStore(),
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(),  # type: ignore[call-arg]
        # Zitadel often issues opaque (non-JWT) access tokens even when the app
        # is configured for JWT. Verify the OIDC id_token instead so the
        # token-swap after /token succeeds; otherwise every /mcp call returns
        # invalid_token despite a successful login.
        verify_id_token=True,
        # Require only identity scopes Zitadel reliably grants. Custom mcp:*
        # scopes must stay advertised (factory valid_scopes / authorize scope)
        # but not required — RequireAuthMiddleware 403s on any missing grant.
        required_scopes=[
            "openid",
            "profile",
            "urn:zitadel:iam:user:resourceowner",
        ],
    )

    tools_provider = FileSystemProvider(Path(__file__).parent / "tools")

    mcp = FastMCP(
        "Knowledge Base Search",
        instructions=SERVER_CITATION_INSTRUCTIONS,
        auth=oidc_proxy,
        providers=[tools_provider],
    )

    mcp.mount(get_custom_routes_provider())

    middleware = [
        Middleware(
            CORSMiddleware,
            # MCP clients authenticate via the Authorization header, not cookies,
            # so credentials aren't needed here. allow_credentials=True combined
            # with a wildcard origin makes starlette reflect any Origin verbatim
            # instead of "*" — a credentialed-CORS hole. Keep it False.
            allow_credentials=False,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    # fastmcp >= 3.4.3 validates Host and Origin headers (DNS-rebinding
    # protection; 421/403 otherwise). Behind a reverse proxy / PaaS the public
    # hostname differs from the bind address AND TLS terminates upstream (the
    # container sees scheme=http while browser Origins are https), so both the
    # public host and the public origin must be allowlisted explicitly.
    public = server_settings.public_base_url
    public_host = public.host if public else None
    public_origin = f"{public.scheme}://{public.host}" if public else None
    mcp.run(
        transport=server_settings.transport_scheme,
        host=server_settings.local_base_url.host,
        port=server_settings.local_base_url.port,
        log_level="debug",
        middleware=middleware,
        allowed_hosts=[public_host] if public_host else None,
        allowed_origins=[public_origin] if public_origin else None,
    )


if __name__ == "__main__":
    main()
