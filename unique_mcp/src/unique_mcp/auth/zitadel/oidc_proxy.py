from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp.server.auth.oidc_proxy import OIDCProxy
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.util.find_env_file import find_env_file

if TYPE_CHECKING:
    from key_value.aio.protocols import AsyncKeyValue


class ZitadelOIDCProxySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_env_file(filenames=["zitadel.env", ".env"], required=False),
        env_prefix="ZITADEL_",
        extra="ignore",
    )

    base_url: str
    client_id: str
    client_secret: str

    @property
    def config_url(self) -> str:
        """Get the Zitadel OIDC configuration endpoint URL."""
        return f"{self.base_url}/.well-known/openid-configuration"


def create_zitadel_oidc_proxy(
    *,
    mcp_server_base_url: str = "http://localhost:8003",
    zitadel_oidc_proxy_settings: ZitadelOIDCProxySettings | None = None,
    client_storage: AsyncKeyValue | None = None,
    **kwargs: Any,
) -> OIDCProxy:
    """Create a Zitadel OIDC proxy instance.

    Args:
        mcp_server_base_url: Base URL of the MCP server (e.g., http://localhost:8003).
        zitadel_oidc_proxy_settings: Optional settings instance. If not provided,
            a new instance will be created.

    Returns:
        Configured OIDCProxy instance
    """
    settings = zitadel_oidc_proxy_settings or ZitadelOIDCProxySettings()  # type: ignore[call-arg]

    return OIDCProxy(
        config_url=settings.config_url,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        base_url=mcp_server_base_url,
        token_endpoint_auth_method="client_secret_post",
        client_storage=client_storage,
        **kwargs,
    )
