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
            Avoid putting custom scopes (``mcp:*``, ``email``, …) in
            ``required_scopes``: Zitadel often omits unrecognised or non-granted
            scopes from the token response. With ``verify_id_token=False`` (the
            default) that wires them into the JWT verifier → ``invalid_token`` on
            every request. With ``verify_id_token=True``, FastMCP withholds them
            from the verifier but still sets ``OIDCProxy.required_scopes`` and
            ``RequireAuthMiddleware`` enforces them against the upstream-granted
            scope list → ``403 insufficient_scope`` instead. Advertise the full
            list via ``valid_scopes`` / authorize ``scope``; require only identity
            scopes Zitadel reliably grants (``openid``, ``profile``,
            ``urn:zitadel:iam:user:resourceowner``).

    Returns:
        Configured OIDCProxy instance
    """
    # Keyword-only + no default only blocks omission. Explicit None still reaches
    # FastMCP's per-pod on-disk fallback — the footgun this argument exists to kill.
    if client_storage is None:
        raise ValueError(
            "client_storage must not be None; pass an AsyncKeyValue backend "
            "(e.g. MemoryStore() for local single-process dev)."
        )

    settings = zitadel_oidc_proxy_settings or ZitadelOIDCProxySettings()  # type: ignore[call-arg]

    extra_authorize_params: dict[str, str] = dict(
        kwargs.pop("extra_authorize_params", None) or {}
    )
    if "scope" not in extra_authorize_params:
        extra_authorize_params["scope"] = " ".join(ZITADEL_DEFAULT_MCP_SCOPES)

    # Advertise / accept these scopes for DCR and /authorize. Do NOT pass the
    # full list as ``required_scopes``: Zitadel may omit custom scopes, and
    # FastMCP enforces ``required_scopes`` either in the JWT verifier
    # (verify_id_token=False → invalid_token) or via RequireAuthMiddleware
    # (verify_id_token=True → insufficient_scope). Callers that need
    # required_scopes should pass a short identity-only list explicitly.
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
