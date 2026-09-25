"""Shared proxy settings consumed by the search proxy and the web-search tool."""

from __future__ import annotations

import os
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProxyAuthMode = Literal["none", "username_password", "ssl_tls"]
ProxyProtocol = Literal["http", "https"]

_REMOVED_SETTINGS: dict[str, str] = {
    "PROXY_USERNAME_SOURCE": (
        "The proxy username is always the service account from proxy_username. "
        "To attribute egress to the end user, set proxy_user_id_header instead."
    ),
    "PROXY_USERNAME_METADATA_FIELD": "Renamed to proxy_user_id_metadata_field.",
    "PER_USER_PROXY_COMPANY_IDS": (
        "Per-company gating is gone. The end-user UID header applies to every "
        "company whenever proxy_user_id_header is set."
    ),
}


class ProxySettings(BaseSettings):
    """Corporate proxy configuration shared by egress clients.

    Two orthogonal concerns, deliberately kept apart:

    * **Authentication** — who *this service* is. ``proxy_username`` and
      ``proxy_password`` become ``Proxy-Authorization: Basic`` on the ``CONNECT``.
      One identity per deployment.
    * **Attribution** — who the *end user* is. ``proxy_user_id_header`` names a
      header carried on the same ``CONNECT``, resolved per request.

    Subclasses set ``model_config`` with their own ``env_prefix``. Concrete
    deployments may override secret fields with a richer SecretStr subclass.
    """

    model_config = SettingsConfigDict(extra="ignore")

    proxy_auth_mode: ProxyAuthMode = "none"
    proxy_protocol: ProxyProtocol = "http"
    proxy_host: str | None = None
    proxy_port: int | None = None
    proxy_headers: dict[str, SecretStr] = Field(
        default_factory=dict,
        description=(
            "Extra headers sent on the CONNECT to the proxy — never to the "
            "target. Do not put credentials here; use proxy_username and "
            "proxy_password, which produce a correct Proxy-Authorization."
        ),
    )
    proxy_ssl_ca_bundle_path: str | None = None
    proxy_username: SecretStr | None = None
    proxy_password: SecretStr = Field(default_factory=lambda: SecretStr(""))
    proxy_ssl_cert_path: str | None = None
    proxy_ssl_key_path: str | None = None

    proxy_user_id_header: str | None = Field(
        default=None,
        description=(
            "Header carrying the requesting end user's ID on the CONNECT to the "
            "proxy, so the proxy can attribute egress to a person while still "
            "authenticating this service. Unset means no UID is sent. Set it to "
            "whatever field the corporate proxy already understands."
        ),
    )
    proxy_user_id_metadata_field: str = Field(
        default="userName",
        description=(
            "User-metadata field whose value becomes the proxy_user_id_header "
            "value. Must name a field the platform stamps after merging user "
            "configuration (userName, email); user-supplied keys are spoofable."
        ),
    )
    http_client_cache_size: int = Field(default=128, ge=1)
    pool_timeout_seconds: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20

    @model_validator(mode="after")
    def _reject_removed_settings(self) -> Self:
        """Fail loudly on retired env vars rather than ignoring them.

        ``extra="ignore"`` would silently drop these, so a deployment carrying
        the old per-user-proxy config would boot and quietly stop attributing
        egress to anyone.
        """
        prefix = self.model_config.get("env_prefix") or ""
        for suffix, guidance in _REMOVED_SETTINGS.items():
            name = f"{prefix}{suffix}"
            if name in os.environ:
                raise ValueError(f"{name} is no longer supported. {guidance}")
        return self

    @model_validator(mode="after")
    def _validate_proxy_config(self) -> Self:
        host_set = self.proxy_host is not None
        port_set = self.proxy_port is not None
        if host_set != port_set:
            raise ValueError("proxy_host and proxy_port must be set together")

        if self.proxy_user_id_header is not None and not host_set:
            raise ValueError(
                "proxy_host and proxy_port must be configured when "
                "proxy_user_id_header is set",
            )

        if self.proxy_auth_mode == "username_password" and self.proxy_username is None:
            raise ValueError(
                "proxy_username is required when proxy_auth_mode is username_password",
            )

        if self.proxy_auth_mode == "ssl_tls" and self.proxy_ssl_cert_path is None:
            raise ValueError(
                "proxy_ssl_cert_path is required when proxy_auth_mode is ssl_tls",
            )
        return self

    @property
    def proxy_configured(self) -> bool:
        """Whether egress goes through a forward proxy at all."""
        return self.proxy_host is not None and self.proxy_port is not None


__all__ = [
    "ProxyAuthMode",
    "ProxyProtocol",
    "ProxySettings",
]
