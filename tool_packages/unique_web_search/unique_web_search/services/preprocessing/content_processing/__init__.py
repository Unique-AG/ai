from unique_web_search.services.preprocessing.content_processing.base import (
    ContentProcessingStartegy,
    ContentProcessingStrategyConfig,
)
from unique_web_search.services.preprocessing.content_processing.strategies import (
    SummarizeWebpageConfig,
    TruncatePageToMaxTokensConfig,
    get_strategy,
)

ProcessingStrategyType = SummarizeWebpageConfig | TruncatePageToMaxTokensConfig

__all__ = [
    "ContentProcessingStartegy",
    "ContentProcessingStrategyConfig",
    "get_strategy",
]
