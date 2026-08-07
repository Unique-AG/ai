from typing import TYPE_CHECKING, Any

from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.auth.zitadel.scopes import ZITADEL_DEFAULT_MCP_SCOPES
from unique_mcp.util.find_env_file import find_env_file

if TYPE_CHECKING:
    from key_value.aio.protocols import AsyncKeyValue


class ZitadelOAuthProxySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(filenames=["zitadel.env", ".env"], required=False),
        env_prefix="ZITADEL_",
        extra="allow",
    )

    base_url: str = "http://localhost:10116"
    client_id: str = "default_client_id"
    client_secret: str = "default_client_secret"

    @property
    def jwks_uri(self) -> str:
        return f"{self.base_url}/oauth/v2/keys"

    @property
    def token_endpoint(self) -> str:
        return f"{self.base_url}/oauth/v2/token"

    @property
    def revoke_endpoint(self) -> str:
        return f"{self.base_url}/oauth/v2/revoke"

    @property
    def authorize_endpoint(self) -> str:
        return f"{self.base_url}/oauth/v2/authorize"

    @property
    def userinfo_endpoint(self) -> str:
        return f"{self.base_url}/oidc/v1/userinfo"

    @property
    def introspect_endpoint(self) -> str:
        return f"{self.base_url}/oauth/v2/introspect"


def create_zitadel_oauth_proxy(
    *,
    client_storage: "AsyncKeyValue",
    mcp_server_base_url: str = "http://localhost:8003",
    zitadel_oauth_proxy_settings: ZitadelOAuthProxySettings | None = None,
    **kwargs: Any,
) -> OAuthProxy:
    """Create a Zitadel OAuth proxy instance.

    Args:
        client_storage: Storage backend for OAuth client/token state. Required:
            FastMCP's own default is an on-disk store under the user's home
            directory, which is a footgun in a container — it may not exist on a
            read-only root filesystem (crash on boot), and even when writable it
            is per-pod, so every restart loses the store that FastMCP's reference
            tokens depend on for JTI lookup, logging out every user on every
            restart/rollout. In a multi-replica or containerized deployment, pass
            a shared backend (e.g. a database-backed ``AsyncKeyValue`` with
            encryption at rest); see the "Production storage" section in
            ``unique_mcp/docs/zitadel/README.md``. For local single-process dev
            where losing sessions on restart is acceptable, pass an in-memory
            store explicitly (e.g. ``key_value.aio.stores.memory.MemoryStore()``).
        mcp_server_base_url: Base URL of the MCP server (e.g., http://localhost:8003).
        zitadel_oauth_proxy_settings: Optional settings instance. If not provided,
            a new instance will be created from environment variables.
        **kwargs: Forwarded directly to ``OAuthProxy``.

    Returns:
        Configured OAuthProxy instance
    """
    if client_storage is None:
        raise ValueError(
            "client_storage must not be None; pass an AsyncKeyValue backend "
            "(e.g. MemoryStore() for local single-process dev)."
        )

    settings = zitadel_oauth_proxy_settings or ZitadelOAuthProxySettings()

    token_verifier = JWTVerifier(
        jwks_uri=settings.jwks_uri,
        issuer=settings.base_url,  # Issuer is Zitadel's URL
        algorithm=None,
        audience=None,
        # required_scopes=[],
    )

    valid_scopes = kwargs.pop("valid_scopes", ZITADEL_DEFAULT_MCP_SCOPES)

    return OAuthProxy(
        upstream_authorization_endpoint=settings.authorize_endpoint,
        upstream_token_endpoint=settings.token_endpoint,
        upstream_client_id=settings.client_id,
        upstream_client_secret=settings.client_secret,
        upstream_revocation_endpoint=settings.revoke_endpoint,
        token_verifier=token_verifier,
        base_url=mcp_server_base_url,
        redirect_path=None,
        issuer_url=None,
        service_documentation_url=None,
        allowed_client_redirect_uris=None,
        valid_scopes=valid_scopes,
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",
        extra_authorize_params=None,
        extra_token_params=None,
        client_storage=client_storage,
        **kwargs,
    )
