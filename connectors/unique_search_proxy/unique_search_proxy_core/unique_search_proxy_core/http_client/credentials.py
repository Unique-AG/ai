"""Resolve the identity an outbound request presents to the corporate proxy."""

from __future__ import annotations

from dataclasses import dataclass

from unique_search_proxy_core.context import RequestContext
from unique_search_proxy_core.errors import ValidationProxyError
from unique_search_proxy_core.http_client.secrets import read_secret
from unique_search_proxy_core.http_client.settings import ProxySettings


@dataclass(frozen=True)
class ProxyIdentity:
    """What distinguishes one proxy connection from another, and the cache key.

    ``username``/``password`` authenticate *this service* to the proxy;
    ``end_user_id`` attributes the request to a person. The end user belongs here
    rather than beside the request because it travels on the ``CONNECT``, which is
    fixed when the connection is established — so two end users can never share
    a pooled connection.
    """

    username: str = ""
    password: str = ""
    end_user_id: str = ""

    @property
    def is_anonymous(self) -> bool:
        """Whether the proxy hop carries no ``Proxy-Authorization``."""
        return self.username == ""


def _resolve_end_user_id(settings: ProxySettings, context: RequestContext) -> str:
    if settings.proxy_user_id_header is None:
        return ""

    field_name = settings.proxy_user_id_metadata_field
    value = context.user_metadata.get(field_name)
    if not isinstance(value, str) or not value.strip():
        # Fail closed: an unattributable request is exactly what the UID header
        # exists to prevent, so never fall back to sending none.
        raise ValidationProxyError(
            f"User metadata field '{field_name}' is required to attribute "
            "egress to the requesting end user",
        )
    return value.strip()


def resolve_identity(
    settings: ProxySettings,
    context: RequestContext,
) -> ProxyIdentity:
    """Build the proxy identity for one request."""
    end_user_id = _resolve_end_user_id(settings, context)

    if settings.proxy_auth_mode != "username_password":
        return ProxyIdentity(end_user_id=end_user_id)

    username = read_secret(settings.proxy_username)
    if not username:
        raise ValidationProxyError(
            "proxy_username is required for username_password proxy auth",
        )
    return ProxyIdentity(
        username=username,
        password=read_secret(settings.proxy_password),
        end_user_id=end_user_id,
    )


__all__ = [
    "ProxyIdentity",
    "resolve_identity",
]
