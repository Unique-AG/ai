from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastmcp.server.auth.oidc_proxy import OIDCProxy
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_mcp.auth.zitadel.scopes import ZITADEL_DEFAULT_MCP_SCOPES
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
    client_storage: AsyncKeyValue,
    mcp_server_base_url: str = "http://localhost:8003",
    zitadel_oidc_proxy_settings: ZitadelOIDCProxySettings | None = None,
    **kwargs: Any,
) -> OIDCProxy:
    """Create a Zitadel OIDC proxy instance.

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
        zitadel_oidc_proxy_settings: Optional settings instance. If not provided,
            a new instance will be created from environment variables.
        **kwargs: Forwarded directly to ``OIDCProxy``. Unless ``extra_authorize_params``
            already sets ``scope``, the default Zitadel/MCP scope list is injected so
            Zitadel never receives an empty scope on the authorize request.
            With ``verify_id_token=False`` (the default), avoid passing
            ``required_scopes``: it is wired into the JWT verifier, and Zitadel access
            tokens often omit several requested scopes from the JWT, which would cause
            the verifier to reject every token (invalid_token loop). With
            ``verify_id_token=True``, FastMCP already excludes ``required_scopes`` from
            the verifier and instead applies it via ``update_default_scopes`` (see
            ``fastmcp/server/auth/oidc_proxy.py``), so passing ``required_scopes`` is
            safe in that mode and the ``valid_scopes`` handling below is redundant.

    Returns:
        Configured OIDCProxy instance
    """
    settings = zitadel_oidc_proxy_settings or ZitadelOIDCProxySettings()  # type: ignore[call-arg]

    extra_authorize_params: dict[str, str] = dict(
        kwargs.pop("extra_authorize_params", None) or {}
    )
    if "scope" not in extra_authorize_params:
        extra_authorize_params["scope"] = " ".join(ZITADEL_DEFAULT_MCP_SCOPES)

    # Advertise / accept these scopes for DCR and /authorize. With the default
    # verify_id_token=False, do NOT pass them as ``required_scopes`` to OIDCProxy:
    # that wires them into the JWT verifier, and Zitadel access tokens often omit
    # scopes from the JWT → invalid_token loop. With verify_id_token=True, FastMCP
    # itself calls update_default_scopes for required_scopes, making this manual
    # call redundant in that mode (see fastmcp/server/auth/oidc_proxy.py).
    valid_scopes = kwargs.pop("valid_scopes", ZITADEL_DEFAULT_MCP_SCOPES)

    proxy = OIDCProxy(
        config_url=settings.config_url,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        base_url=mcp_server_base_url,
        token_endpoint_auth_method="client_secret_post",
        client_storage=client_storage,
        extra_authorize_params=extra_authorize_params,
        **kwargs,
    )
    # OIDCProxy does not forward ``valid_scopes`` to OAuthProxy; set them after init
    # so metadata ``scopes_supported`` and DCR accept openid/profile/mcp:* scopes.
    if valid_scopes:
        proxy.update_default_scopes(list(valid_scopes))
    return proxy
