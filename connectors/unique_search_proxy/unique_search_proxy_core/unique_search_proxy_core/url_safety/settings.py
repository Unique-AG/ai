from __future__ import annotations

from enum import StrEnum
from logging import getLogger

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_search_proxy_core.http_client.settings import ProxySettings

_LOGGER = getLogger(__name__)


class UrlSafetyMode(StrEnum):
    APPLICATION = "APPLICATION"
    DISABLED_WITH_CORPORATE_PROXY = "DISABLED_WITH_CORPORATE_PROXY"


class UrlSafetySettings(BaseSettings):
    mode: UrlSafetyMode = Field(
        default=UrlSafetyMode.APPLICATION,
        description=(
            "APPLICATION enforces SSRF protection in the application. "
            "DISABLED_WITH_CORPORATE_PROXY bypasses application URL checks and "
            "requires every request to use the configured corporate proxy; the "
            "application does not verify the proxy's URL-safety policy."
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
    """Reject disabled mode unless every request uses a configured proxy."""
    if url_safety.mode is not UrlSafetyMode.DISABLED_WITH_CORPORATE_PROXY:
        return

    if (
        not proxy.proxy_host
        or proxy.proxy_port is None
        or not 1 <= proxy.proxy_port <= 65535
    ):
        raise ValueError(
            "URL safety mode DISABLED_WITH_CORPORATE_PROXY requires a non-empty "
            "proxy_host and a valid proxy_port",
        )

    uses_authenticated_proxy = proxy.proxy_auth_mode != "none"
    uses_proxy_for_every_user = (
        proxy.proxy_username_source == "user_metadata"
        and not proxy.per_user_proxy_company_ids
    )
    if not uses_authenticated_proxy and not uses_proxy_for_every_user:
        raise ValueError(
            "URL safety mode DISABLED_WITH_CORPORATE_PROXY requires every request "
            "to use the corporate proxy",
        )

    if proxy.proxy_auth_mode == "ssl_tls" and proxy.proxy_ssl_cert_path is None:
        raise ValueError(
            "URL safety mode DISABLED_WITH_CORPORATE_PROXY with ssl_tls "
            "authentication requires proxy_ssl_cert_path",
        )


url_safety_settings = UrlSafetySettings()
_LOGGER.info("URL safety mode: %s", url_safety_settings.mode)
