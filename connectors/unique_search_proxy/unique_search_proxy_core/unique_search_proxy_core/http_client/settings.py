"""Shared proxy settings consumed by the search proxy and the web-search tool."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProxyAuthMode = Literal["none", "username_password", "ssl_tls"]
ProxyProtocol = Literal["http", "https"]
ProxyUsernameSource = Literal["settings", "user_metadata"]


class ProxySettings(BaseSettings):
    """Corporate proxy configuration shared by egress clients.

    Subclasses set ``model_config`` with their own ``env_prefix``. Concrete
    deployments may override secret fields with a richer SecretStr subclass.
    """

    model_config = SettingsConfigDict(extra="ignore")

    proxy_auth_mode: ProxyAuthMode = "none"
    proxy_protocol: ProxyProtocol = "http"
    proxy_host: str | None = None
    proxy_port: int | None = None
    proxy_headers: dict[str, SecretStr] = Field(default_factory=dict)
    proxy_ssl_ca_bundle_path: str | None = None
    proxy_username: SecretStr | None = None
    proxy_password: SecretStr = Field(default_factory=lambda: SecretStr(""))
    proxy_ssl_cert_path: str | None = None
    proxy_ssl_key_path: str | None = None

    proxy_username_source: ProxyUsernameSource = Field(
        default="settings",
        description=(
            "Where the proxy username comes from: fixed settings, or a field on "
            "the request's user metadata."
        ),
    )
    proxy_username_metadata_field: str = Field(
        default="userName",
        description=(
            "User-metadata field whose value becomes the proxy username when "
            "proxy_username_source is user_metadata. Must name a field the "
            "platform stamps after merging user configuration (userName, "
            "email); user-supplied keys are spoofable."
        ),
    )
    per_user_proxy_company_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Company IDs whose egress authenticates as the end user when "
            "proxy_username_source is user_metadata. Empty means every company."
        ),
    )
    http_client_cache_size: int = Field(default=128, ge=1)
    pool_timeout_seconds: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20

    @model_validator(mode="after")
    def _validate_proxy_credentials_config(self) -> Self:
        if self.proxy_username_source == "user_metadata":
            if self.proxy_host is None or self.proxy_port is None:
                raise ValueError(
                    "Proxy host and port must be configured when "
                    "proxy_username_source is user_metadata",
                )
        if (
            self.proxy_auth_mode == "username_password"
            and self.proxy_username_source == "settings"
            and self.proxy_username is None
        ):
            raise ValueError(
                "proxy_username is required when proxy_auth_mode is "
                "username_password and proxy_username_source is settings",
            )
        return self

    def per_user_proxy_enabled_for(self, company_id: str) -> bool:
        """Whether a company's egress must authenticate from user metadata."""
        if self.proxy_username_source != "user_metadata":
            return False
        if not self.per_user_proxy_company_ids:
            return True
        return company_id in self.per_user_proxy_company_ids
