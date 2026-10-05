from __future__ import annotations

from logging import getLogger

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_search_proxy_core.http_client.settings import ProxySettings

_LOGGER = getLogger(__name__)
_PROXY_REMEDIATION = (
    "Either set URL_SAFETY_ENABLED=true to enable application URL-safety checks, "
    "or configure an authenticated corporate proxy for all egress."
)


class UrlSafetySettings(BaseSettings):
    enabled: bool = Field(
        default=True,
        description=(
            "Whether the application enforces URL-safety checks. Setting this to "
            "false bypasses application checks and requires every request to use "
            "a configured corporate proxy; the application does not verify the "
            "proxy's URL-safety policy."
        ),
    )
    resolve_redirects: bool = True
    allowed_schemes: list[str] = ["http", "https"]
    localhost_hosts: list[str] = [
        "localhost",
        "localhost.localdomain",
    ]
    metadata_hosts: list[str] = [
        "100.100.100.200",  # Alibaba Cloud
        "169.254.169.254",  # AWS / GCP / Azure IMDS
        "169.254.170.2",  # AWS ECS task credentials
        "metadata.azure.internal",
        "metadata.google.internal",
    ]
    cluster_local_suffix: str = ".cluster.local"
    service_suffix: str = ".svc"
    max_redirect_hops: int = 10
    redirect_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="URL_SAFETY_",
        case_sensitive=False,
        frozen=True,
    )


def validate_url_safety_proxy_configuration(
    url_safety: UrlSafetySettings,
    proxy: ProxySettings,
) -> None:
    """Reject disabled application checks without compatible proxy routing."""
    if url_safety.enabled:
        return

    if (
        not proxy.proxy_host
        or proxy.proxy_port is None
        or not 1 <= proxy.proxy_port <= 65535
    ):
        raise ValueError(
            "URL_SAFETY_ENABLED=false disables application URL-safety checks, "
            "but no usable corporate proxy endpoint is configured: proxy_host "
            "must be non-empty and proxy_port must be between 1 and 65535. "
            + _PROXY_REMEDIATION,
        )

    uses_authenticated_proxy = proxy.proxy_auth_mode != "none"
    uses_proxy_for_every_user = (
        proxy.proxy_username_source == "user_metadata"
        and not proxy.per_user_proxy_company_ids
    )
    if not uses_authenticated_proxy and not uses_proxy_for_every_user:
        raise ValueError(
            "URL_SAFETY_ENABLED=false disables application URL-safety checks, "
            "but the current proxy settings do not route every request through "
            "an authenticated corporate proxy. Direct or partially proxied "
            "egress is incompatible. " + _PROXY_REMEDIATION,
        )

    if proxy.proxy_auth_mode == "ssl_tls" and proxy.proxy_ssl_cert_path is None:
        raise ValueError(
            "URL_SAFETY_ENABLED=false disables application URL-safety checks, "
            "but SSL/TLS proxy authentication is missing proxy_ssl_cert_path. "
            + _PROXY_REMEDIATION,
        )


url_safety_settings = UrlSafetySettings()
if url_safety_settings.enabled:
    _LOGGER.info("Application URL safety checks are enabled")
else:
    _LOGGER.warning(
        "Application URL safety checks are disabled because "
        "URL_SAFETY_ENABLED=false. All egress must use a configured corporate "
        "proxy. Note: the corporate proxy URL-safety policy is not verified by "
        "the application."
    )
