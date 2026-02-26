from typing import TYPE_CHECKING, Any

from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    mcp_server_base_url: str = "http://localhost:8003",
    zitadel_oauth_proxy_settings: ZitadelOAuthProxySettings | None = None,
    client_storage: "AsyncKeyValue | None" = None,
    **kwargs: Any,
) -> OAuthProxy:
    """Create a Zitadel OAuth proxy instance.

    Args:
        server_base_url: Base URL of the MCP server (e.g., http://localhost:8003).

    Returns:
        Configured OAuthProxy instance
    """
    settings = zitadel_oauth_proxy_settings or ZitadelOAuthProxySettings()

    token_verifier = JWTVerifier(
        jwks_uri=settings.jwks_uri,
        issuer=settings.base_url,  # Issuer is Zitadel's URL
        algorithm=None,
        audience=None,
        # required_scopes=[],
    )

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
        valid_scopes=[
            "mcp:tools",
            "mcp:prompts",
            "mcp:resources",
            "mcp:resource-templates",
            "email",
            "openid",
            "profile",
            "urn:zitadel:iam:user:resourceowner",
        ],
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",
        extra_authorize_params=None,
        extra_token_params=None,
        client_storage=client_storage,
        **kwargs,
    )
