from fastmcp.server.auth.oidc_proxy import OIDCProxy
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.util.find_env_file import find_env_file


class KeycloakOAuthProxySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(filenames=["keycloak.env", ".env"], required=False),
        env_prefix="KEYCLOAK_",
        extra="allow",
    )

    base_url: str = Field(..., description="The base URL for the Keycloak instance")

    # Keycloak/OIDC settings
    openid_configuration: HttpUrl = Field(
        ..., description="The OpenID Connect configuration URL for Keycloak"
    )

    client_id: str = Field(
        ..., min_length=1, description="The client ID for Keycloak authentication"
    )

    client_secret: str = Field(
        ..., min_length=1, description="The client secret for Keycloak authentication"
    )


def create_keycloak_oidc_proxy(
    *,
    keycloak_oauth_proxy_settings: KeycloakOAuthProxySettings | None = None,
) -> OIDCProxy:
    """Create a Keycloak OAuth proxy instance.

    Args:
        server_base_url: Base URL of the MCP server (e.g., http://localhost:8003).

    Returns:
        Configured OAuthProxy instance
    """
    settings = keycloak_oauth_proxy_settings or KeycloakOAuthProxySettings()  # type: ignore[arg-type] Ignoring type error as settings obtained from env

    oidc_proxy = OIDCProxy(
        config_url=str(settings.openid_configuration),
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        base_url=str(settings.base_url),
    )

    return oidc_proxy
