from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.helm.metadata import helm_settings
from unique_search_proxy_client.web.settings.base import get_settings

APP_ENV_PREFIX = ""


@helm_settings(
    title="Application",
    helm_key=None,
    kind="internal",
    egress=None,
    env_prefix=APP_ENV_PREFIX,
)
class AppSettings(BaseSettings):
    require_context_headers: bool = True


def get_app_settings() -> AppSettings:
    return get_settings(AppSettings, env_prefix=APP_ENV_PREFIX)


app_settings: AppSettings = get_app_settings()

__all__ = [
    "AppSettings",
    "app_settings",
    "get_app_settings",
]
