from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from unique_search_proxy_client.web.settings.base import get_settings

STARTUP_LOG_ENV_PREFIX = "STARTUP_LOG_"


class StartupLogSettings(BaseSettings):
    """Startup log formatting options."""

    secret_suffix_len: int = Field(
        default=0,
        ge=0,
        le=32,
        description=(
            "Number of trailing characters to show when logging secret values "
            "at startup (0 hides the secret entirely)."
        ),
    )


def _get_startup_log_settings() -> StartupLogSettings:
    return get_settings(StartupLogSettings, env_prefix=STARTUP_LOG_ENV_PREFIX)


startup_log_settings = _get_startup_log_settings()
