"""Backward-compatibility shim — re-exports from the new per-mode subpackages.

Prefer importing directly from ``executors.base_config``, ``executors.v1``,
``executors.v2``, or ``executors.v3`` in new code.
"""

from logging import getLogger

from unique_web_search.services.executors.base_config import WebSearchMode
from unique_web_search.services.executors.v1.config import (
    RefineQueryMode,
    WebSearchV1Config,
)
from unique_web_search.services.executors.v2.config import WebSearchV2Config
from unique_web_search.services.executors.v3.config import WebSearchV3Config
from unique_web_search.settings import env_settings

_LOGGER = getLogger(__name__)
WebSearchModeConfig = WebSearchV1Config | WebSearchV2Config | WebSearchV3Config


def get_default_web_search_mode_config() -> WebSearchMode:
    match env_settings.web_search_mode:
        case "v1":
            return WebSearchMode.V1
        case "v2":
            return WebSearchMode.V2
        case "v3":
            return WebSearchMode.V3
        case _:
            raise ValueError(f"Invalid web search mode: {env_settings.web_search_mode}")


__all__ = [
    "WebSearchModeConfig",
    "WebSearchV1Config",
    "WebSearchV2Config",
    "WebSearchV3Config",
    "get_default_web_search_mode_config",
    "WebSearchMode",
    "RefineQueryMode",
]
