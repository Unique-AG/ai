"""Strategies that resolve the proxy username for an outbound request."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError
from unique_search_proxy_core.http_client.secrets import read_secret
from unique_search_proxy_core.http_client.settings import ProxySettings


@dataclass(frozen=True)
class ProxyCredentials:
    """Identity presented to the corporate proxy for one egress client."""

    username: str
    password: str

    @classmethod
    def anonymous(cls) -> ProxyCredentials:
        """Credentials for modes that carry no proxy username (none, ssl_tls)."""
        return cls(username="", password="")

    @property
    def is_anonymous(self) -> bool:
        return self.username == ""


class ProxyCredentialResolver(Protocol):
    """Resolve the proxy credentials that an outbound request must use."""

    def resolve(self, context: RequestContext) -> ProxyCredentials: ...


class SettingsProxyCredentials:
    """Read the proxy username and password from ProxySettings."""

    def __init__(self, settings: ProxySettings) -> None:
        self._settings = settings

    def resolve(self, context: RequestContext) -> ProxyCredentials:
        del context
        if self._settings.proxy_auth_mode != "username_password":
            return ProxyCredentials.anonymous()
        username = read_secret(self._settings.proxy_username)
        if not username:
            raise ValidationProxyError(
                "proxy_username is required for username_password proxy auth",
            )
        return ProxyCredentials(
            username=username,
            password=read_secret(self._settings.proxy_password),
        )


class UserMetadataProxyCredentials:
    """Read the proxy username from request user metadata for gated companies."""

    def __init__(self, settings: ProxySettings) -> None:
        self._settings = settings
        self._fallback = SettingsProxyCredentials(settings)

    def resolve(self, context: RequestContext) -> ProxyCredentials:
        if not self._settings.per_user_proxy_enabled_for(context.company_id):
            return self._fallback.resolve(context)

        field_name = self._settings.proxy_username_metadata_field
        value = context.user_metadata.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValidationProxyError(
                f"User metadata field '{field_name}' is required for "
                "per-user proxy authentication",
            )
        return ProxyCredentials(
            username=value.strip(),
            password=read_secret(self._settings.proxy_password),
        )


def resolver_from_settings(settings: ProxySettings) -> ProxyCredentialResolver:
    """Pick the credential resolver configured on the settings."""
    match settings.proxy_username_source:
        case "settings":
            return SettingsProxyCredentials(settings)
        case "user_metadata":
            return UserMetadataProxyCredentials(settings)
        case _:
            raise ValueError(
                f"Invalid proxy_username_source: {settings.proxy_username_source}",
            )


__all__ = [
    "ProxyCredentials",
    "ProxyCredentialResolver",
    "SettingsProxyCredentials",
    "UserMetadataProxyCredentials",
    "resolver_from_settings",
]
