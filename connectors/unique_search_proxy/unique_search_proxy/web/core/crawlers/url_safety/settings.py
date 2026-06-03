from pydantic_settings import BaseSettings

from unique_search_proxy.web.settings.base import is_test_runtime, settings_config


class UrlSafetySettings(BaseSettings):
    enabled: bool = True
    resolve_redirects: bool = True
    allowed_schemes: list[str] = ["http", "https"]
    localhost_hosts: list[str] = [
        "localhost",
        "localhost.localdomain",
    ]
    metadata_hosts: list[str] = [
        "100.100.100.200",
        "169.254.169.254",
        "169.254.170.2",
        "metadata.azure.internal",
        "metadata.google.internal",
    ]
    cluster_local_suffix: str = ".cluster.local"
    service_suffix: str = ".svc"
    max_redirect_hops: int = 10
    redirect_timeout_seconds: float = 10.0

    model_config = settings_config(env_prefix="URL_SAFETY_")


class UrlSafetySettingsForTests(UrlSafetySettings):
    model_config = settings_config(env_prefix="URL_SAFETY_", test=True)


def get_url_safety_settings() -> UrlSafetySettings:
    if is_test_runtime():
        return UrlSafetySettingsForTests()
    return UrlSafetySettings()


url_safety_settings: UrlSafetySettings = get_url_safety_settings()
