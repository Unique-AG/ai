from logging import getLogger

from unique_web_search.services.executors.configs.base import WebSearchMode
from unique_web_search.services.executors.configs.v1_config import (
    RefineQueryMode,
    WebSearchV1Config,
)
from unique_web_search.services.executors.configs.v2_config import WebSearchV2Config
from unique_web_search.settings import env_settings

_LOGGER = getLogger(__name__)
WebSearchModeConfig = WebSearchV1Config | WebSearchV2Config


def get_default_web_search_mode_config() -> WebSearchMode:
    match env_settings.web_search_mode:
        case "v1":
            return WebSearchMode.V1
        case "v2":
            return WebSearchMode.V2
        case _:
            raise ValueError(f"Invalid web search mode: {env_settings.web_search_mode}")


__all__ = [
    "WebSearchModeConfig",
    "get_default_web_search_mode_config",
    "WebSearchMode",
    "RefineQueryMode",
]
