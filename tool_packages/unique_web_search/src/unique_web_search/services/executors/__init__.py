from logging import getLogger

from unique_web_search.services.executors.base_config import WebSearchMode
from unique_web_search.services.executors.context import (
    ExecutorCallbacks,
    ExecutorConfiguration,
    ExecutorServiceContext,
)
from unique_web_search.services.executors.v1.config import (
    RefineQueryMode,
    WebSearchV1Config,
)
from unique_web_search.services.executors.v1.executor import (
    WebSearchV1Executor,
)
from unique_web_search.services.executors.v2.config import WebSearchV2Config
from unique_web_search.services.executors.v2.executor import (
    WebSearchV2Executor,
)
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
    "WebSearchV1Config",
    "WebSearchV2Config",
    "get_default_web_search_mode_config",
    "WebSearchMode",
    "RefineQueryMode",
    "WebSearchV1Executor",
    "WebSearchV2Executor",
    "ExecutorServiceContext",
    "ExecutorConfiguration",
    "ExecutorCallbacks",
]
