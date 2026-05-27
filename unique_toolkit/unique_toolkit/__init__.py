from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unique_toolkit.chat import ChatService as ChatService
    from unique_toolkit.content import ContentService as ContentService
    from unique_toolkit.data_extraction import (
        StructuredOutputDataExtractor as StructuredOutputDataExtractor,
    )
    from unique_toolkit.data_extraction import (
        StructuredOutputDataExtractorConfig as StructuredOutputDataExtractorConfig,
    )
    from unique_toolkit.embedding import EmbeddingService as EmbeddingService
    from unique_toolkit.framework_utilities.openai.client import (
        get_async_openai_client as get_async_openai_client,
    )
    from unique_toolkit.framework_utilities.openai.client import (
        get_openai_client as get_openai_client,
    )
    from unique_toolkit.language_model import (
        LanguageModelMessages as LanguageModelMessages,
    )
    from unique_toolkit.language_model import LanguageModelName as LanguageModelName
    from unique_toolkit.language_model import (
        LanguageModelService as LanguageModelService,
    )
    from unique_toolkit.language_model import (
        LanguageModelToolDescription as LanguageModelToolDescription,
    )
    from unique_toolkit.services.knowledge_base import (
        KnowledgeBaseService as KnowledgeBaseService,
    )
    from unique_toolkit.short_term_memory import (
        ShortTermMemoryService as ShortTermMemoryService,
    )

_EXPORTS: dict[str, tuple[str, str]] = {
    "ChatService": ("unique_toolkit.chat", "ChatService"),
    "ContentService": ("unique_toolkit.content", "ContentService"),
    "EmbeddingService": ("unique_toolkit.embedding", "EmbeddingService"),
    "get_openai_client": (
        "unique_toolkit.framework_utilities.openai.client",
        "get_openai_client",
    ),
    "get_async_openai_client": (
        "unique_toolkit.framework_utilities.openai.client",
        "get_async_openai_client",
    ),
    "KnowledgeBaseService": (
        "unique_toolkit.services.knowledge_base",
        "KnowledgeBaseService",
    ),
    "LanguageModelMessages": (
        "unique_toolkit.language_model",
        "LanguageModelMessages",
    ),
    "LanguageModelName": ("unique_toolkit.language_model", "LanguageModelName"),
    "LanguageModelService": ("unique_toolkit.language_model", "LanguageModelService"),
    "LanguageModelToolDescription": (
        "unique_toolkit.language_model",
        "LanguageModelToolDescription",
    ),
    "ShortTermMemoryService": (
        "unique_toolkit.short_term_memory",
        "ShortTermMemoryService",
    ),
    "StructuredOutputDataExtractor": (
        "unique_toolkit.data_extraction",
        "StructuredOutputDataExtractor",
    ),
    "StructuredOutputDataExtractorConfig": (
        "unique_toolkit.data_extraction",
        "StructuredOutputDataExtractorConfig",
    ),
}

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


def __getattr__(name: str) -> Any:
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    return getattr(import_module(module_name), attribute_name)
