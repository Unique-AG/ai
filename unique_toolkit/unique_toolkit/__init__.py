from importlib.util import find_spec
from typing import TYPE_CHECKING

from ._common._lazy import install as _install

if TYPE_CHECKING:
    from unique_toolkit._common.config_checker import (
        ConfigDiffer as ConfigDiffer,
    )
    from unique_toolkit._common.config_checker import (
        ConfigEntry as ConfigEntry,
    )
    from unique_toolkit._common.config_checker import (
        ConfigExporter as ConfigExporter,
    )
    from unique_toolkit._common.config_checker import (
        ConfigRegistry as ConfigRegistry,
    )
    from unique_toolkit._common.config_checker import (
        ConfigValidator as ConfigValidator,
    )
    from unique_toolkit._common.config_checker import (
        DefaultChangeReport as DefaultChangeReport,
    )
    from unique_toolkit._common.config_checker import (
        ExportManifest as ExportManifest,
    )
    from unique_toolkit._common.config_checker import (
        ValidationReport as ValidationReport,
    )
    from unique_toolkit._common.config_checker import (
        register_config as register_config,
    )
    from unique_toolkit.chat import ChatService as ChatService
    from unique_toolkit.content import ContentService as ContentService
    from unique_toolkit.data_extraction import (
        StructuredOutputDataExtractor as StructuredOutputDataExtractor,
    )
    from unique_toolkit.data_extraction import (
        StructuredOutputDataExtractorConfig as StructuredOutputDataExtractorConfig,
    )
    from unique_toolkit.embedding import EmbeddingService as EmbeddingService
    from unique_toolkit.framework_utilities.langchain.client import (
        get_langchain_client as get_langchain_client,
    )
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
    "ConfigDiffer": ("unique_toolkit._common.config_checker", "ConfigDiffer"),
    "ConfigEntry": ("unique_toolkit._common.config_checker", "ConfigEntry"),
    "ConfigExporter": ("unique_toolkit._common.config_checker", "ConfigExporter"),
    "ConfigRegistry": ("unique_toolkit._common.config_checker", "ConfigRegistry"),
    "ConfigValidator": ("unique_toolkit._common.config_checker", "ConfigValidator"),
    "DefaultChangeReport": (
        "unique_toolkit._common.config_checker",
        "DefaultChangeReport",
    ),
    "ExportManifest": ("unique_toolkit._common.config_checker", "ExportManifest"),
    "ValidationReport": ("unique_toolkit._common.config_checker", "ValidationReport"),
    "register_config": ("unique_toolkit._common.config_checker", "register_config"),
    "get_langchain_client": (
        "unique_toolkit.framework_utilities.langchain.client",
        "get_langchain_client",
    ),
}

_OPTIONAL_EXPORTS = frozenset(  # dependency could be missing (optional)
    {
        "ConfigDiffer",
        "ConfigEntry",
        "ConfigExporter",
        "ConfigRegistry",
        "ConfigValidator",
        "DefaultChangeReport",
        "ExportManifest",
        "ValidationReport",
        "register_config",
        "get_langchain_client",
    }
)

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

if find_spec("deepdiff") is not None and find_spec("pydantic_settings") is not None:
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
if find_spec("langchain_openai") is not None:
    __all__.append("get_langchain_client")


_install(globals(), _EXPORTS, optional=_OPTIONAL_EXPORTS)
