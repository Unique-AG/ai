from __future__ import annotations

import logging

from pydantic import Field
from pydantic_settings import BaseSettings

from unique_search_proxy.web.settings.base import settings_config

_LOGGER = logging.getLogger(__name__)

_DEFAULT_API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

_google_search_settings: GoogleSearchSettings | None = None


class GoogleSearchSettings(BaseSettings):
    """Environment-backed credentials for Google Custom Search."""

    model_config = settings_config()

    google_search_api_key: str | None = None
    google_search_api_endpoint: str | None = Field(default=_DEFAULT_API_ENDPOINT)
    google_search_engine_id: str | None = None

    @property
    def is_configured(self) -> bool:
        return bool(
            self.google_search_api_key
            and self.google_search_engine_id
            and self.google_search_api_endpoint,
        )

    @classmethod
    def from_env(cls) -> GoogleSearchSettings:
        settings = cls()
        if not settings.is_configured:
            missing: list[str] = []
            if not settings.google_search_api_key:
                missing.append("API key")
            if not settings.google_search_engine_id:
                missing.append("engine ID")
            if not settings.google_search_api_endpoint:
                missing.append("API endpoint")
            _LOGGER.warning(
                "Google Search API missing required settings: %s",
                ", ".join(missing),
            )
        else:
            _LOGGER.info("Google Search API is properly configured")
        return settings


def get_google_search_settings() -> GoogleSearchSettings:
    global _google_search_settings
    if _google_search_settings is None:
        _google_search_settings = GoogleSearchSettings.from_env()
    return _google_search_settings


def reset_google_search_settings_for_tests() -> None:
    global _google_search_settings
    _google_search_settings = None
