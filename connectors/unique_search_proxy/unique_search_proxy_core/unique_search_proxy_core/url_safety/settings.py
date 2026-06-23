from __future__ import annotations

from logging import getLogger

from pydantic_settings import BaseSettings, SettingsConfigDict

_LOGGER = getLogger(__name__)


class UrlSafetySettings(BaseSettings):
    enabled: bool = True
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


url_safety_settings = UrlSafetySettings()
_LOGGER.info("URL Safety is enabled: %s", url_safety_settings.enabled)
