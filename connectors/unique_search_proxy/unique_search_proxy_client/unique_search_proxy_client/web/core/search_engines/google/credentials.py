from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from unique_search_proxy_core.errors import EngineNotConfiguredError
from unique_search_proxy_core.search_engines.base import SearchEngineType
from unique_search_proxy_core.search_engines.google.schema import GoogleConfig
from unique_search_proxy_core.search_engines.pagination import PageRequest

from unique_search_proxy_client.web.core.search_engines.google.settings import (
    GoogleSearchSettings,
    get_google_search_settings,
)


@dataclass(frozen=True)
class GoogleCredentials:
    api_key: str
    search_engine_id: str
    api_endpoint: str

    @classmethod
    def from_settings(
        cls,
        settings: GoogleSearchSettings,
        *,
        search_engine_id: str | None = None,
    ) -> GoogleCredentials:
        assert settings.google_search_api_key is not None
        assert settings.google_search_api_endpoint is not None
        resolved_engine_id = search_engine_id or settings.google_search_engine_id
        assert resolved_engine_id is not None
        return cls(
            api_key=settings.google_search_api_key,
            search_engine_id=resolved_engine_id,
            api_endpoint=settings.google_search_api_endpoint,
        )

    @classmethod
    def from_env(cls, *, search_engine_id: str | None = None) -> GoogleCredentials:
        settings = get_google_search_settings()
        if (
            not settings.google_search_api_key
            or not settings.google_search_api_endpoint
        ):
            raise EngineNotConfiguredError(
                SearchEngineType.GOOGLE.value,
                kind="engine",
            )

        resolved_engine_id = search_engine_id or settings.google_search_engine_id
        if not resolved_engine_id:
            raise EngineNotConfiguredError(
                SearchEngineType.GOOGLE.value,
                kind="engine",
            )

        return cls.from_settings(
            settings,
            search_engine_id=resolved_engine_id,
        )


def build_google_query_params(
    *,
    query: str,
    credentials: GoogleCredentials,
    request: BaseModel,
    page: PageRequest,
) -> dict[str, Any]:
    """Assemble the Google API query string from the derived request + credentials."""
    config = GoogleConfig()
    return {
        "q": query,
        "cx": credentials.search_engine_id,
        "key": credentials.api_key,
        "start": page.offset,
        "num": page.count,
        **config.provider_query_params_from(request),
    }


__all__ = [
    "GoogleCredentials",
    "build_google_query_params",
]
