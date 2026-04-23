# Re-export commonly used classes for easier imports
from unique_toolkit.chat import ChatService
from unique_toolkit.content import ContentService
from unique_toolkit.data_extraction import (
    StructuredOutputDataExtractor,
    StructuredOutputDataExtractorConfig,
)
from unique_toolkit.embedding import EmbeddingService
from unique_toolkit.framework_utilities.openai.client import (
    get_async_openai_client,
    get_openai_client,
)
from unique_toolkit.language_model import (
    LanguageModelMessages,
    LanguageModelName,
    LanguageModelService,
    LanguageModelToolDescription,
)
from unique_toolkit.services.knowledge_base import KnowledgeBaseService
from unique_toolkit.short_term_memory import ShortTermMemoryService

# Conditionally import config_checker (requires pydantic-settings)
_CONFIG_CHECKER_AVAILABLE: bool = False
try:
    from unique_toolkit._common.config_checker import (
        ConfigDiffer,  # noqa: F401, I001
        ConfigEntry,  # noqa: F401, I001
        ConfigExporter,  # noqa: F401, I001
        ConfigRegistry,  # noqa: F401, I001
        ConfigValidator,  # noqa: F401, I001
        DefaultChangeReport,  # noqa: F401, I001
        ExportManifest,  # noqa: F401, I001
        ValidationReport,  # noqa: F401, I001
        register_config,  # noqa: F401, I001
    )

    _CONFIG_CHECKER_AVAILABLE = True  # pyright: ignore[reportConstantRedefinition]
except ImportError:
    pass

# Conditionally import langchain utilities if langchain is installed
_LANGCHAIN_AVAILABLE: bool = False
try:
    from unique_toolkit.framework_utilities.langchain.client import get_langchain_client  # noqa: F401, I001

    _LANGCHAIN_AVAILABLE = True  # pyright: ignore[reportConstantRedefinition]
except ImportError:
    pass

# You can add other classes you frequently use here as well

__all__ = [
    "ChatService",
    "ContentService",
    "EmbeddingService",
    "get_openai_client",
    "get_async_openai_client",
    "KnowledgeBaseService",
    "LanguageModelMessages",
    "LanguageModelName",
    "LanguageModelService",
    "LanguageModelToolDescription",
    "ShortTermMemoryService",
    "StructuredOutputDataExtractor",
    "StructuredOutputDataExtractorConfig",
]

# Add config_checker exports if available
if _CONFIG_CHECKER_AVAILABLE:
    __all__.extend(
        [
            "ConfigDiffer",
            "ConfigEntry",
            "ConfigExporter",
            "ConfigRegistry",
            "ConfigValidator",
            "DefaultChangeReport",
            "ExportManifest",
            "ValidationReport",
            "register_config",
        ]
    )
# Add langchain-specific exports if available
if _LANGCHAIN_AVAILABLE:
    __all__.append("get_langchain_client")
