import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class UrlSafetySettings(BaseSettings):
    # URL safety settings
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


def get_model_config(test: bool = False) -> SettingsConfigDict:
    if test:
        env_file = Path(os.getcwd()) / "tests/test.env"
    else:
        env_file = Path(os.getcwd()) / ".env"

    return SettingsConfigDict(
        extra="ignore",
        env_prefix="URL_SAFETY_",
        case_sensitive=False,
        env_file=env_file,
        env_file_encoding="utf-8",
        frozen=True,
    )


class Settings(UrlSafetySettings):
    model_config = get_model_config()


class TestSettings(UrlSafetySettings):
    model_config = get_model_config(test=True)


def get_settings() -> UrlSafetySettings:
    if "pytest" in sys.modules:
        return TestSettings()
    return Settings()


url_safety_settings: UrlSafetySettings = get_settings()
