from fastmcp.server.auth.oidc_proxy import OIDCProxy
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.util.find_env_file import find_env_file


class ZitadelOIDCProxySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(filenames=["zitadel.env", ".env"], required=False),
        env_prefix="ZITADEL_",
        extra="allow",
    )

    base_url: str = Field(
        default="http://localhost:10116",
        description="The base URL for the Zitadel instance",
    )

    # Zitadel/OIDC settings
    openid_configuration: HttpUrl | None = Field(
        default=None,
        description="The OpenID Connect configuration URL for Zitadel. If not provided,"
        " it will be constructed from base_url",
    )

    client_id: str = Field(
        default="default_client_id",
        min_length=1,
        description="The client ID for Zitadel authentication",
    )

    client_secret: str = Field(
        default="default_client_secret",
        min_length=1,
        description="The client secret for Zitadel authentication",
    )

    def get_openid_configuration_url(self) -> str:
        """Get the OpenID Connect configuration URL."""
        if self.openid_configuration:
            return str(self.openid_configuration)
        return f"{self.base_url}/.well-known/openid-configuration"


def create_zitadel_oidc_proxy(
    *,
    zitadel_oidc_proxy_settings: ZitadelOIDCProxySettings | None = None,
) -> OIDCProxy:
    """Create a Zitadel OIDC proxy instance.

    Args:
        zitadel_oidc_proxy_settings: Optional settings for the Zitadel OIDC proxy.
            If not provided, settings will be loaded from environment variables.

    Returns:
        Configured OIDCProxy instance
    """
    settings = zitadel_oidc_proxy_settings or ZitadelOIDCProxySettings()
    # type: ignore[arg-type] Ignoring type error as settings obtained from env

    oidc_proxy = OIDCProxy(
        config_url=settings.get_openid_configuration_url(),
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        base_url=settings.base_url,
    )

    return oidc_proxy
