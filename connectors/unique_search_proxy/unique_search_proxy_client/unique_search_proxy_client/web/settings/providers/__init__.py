"""Upstream provider credentials (search engines, crawlers) loaded from environment."""

from unique_search_proxy_client.web.settings.providers.brave import (
    brave_search_credentials,
)
from unique_search_proxy_client.web.settings.providers.google import (
    google_search_credentials,
)

__all__ = [
    "brave_search_credentials",
    "google_search_credentials",
]
