# Re-export commonly used classes for easier imports
from unique_toolkit.chat import ChatService
from unique_toolkit.content import ContentService
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

# Conditionally import langchain utilities if langchain is installed
try:
    from unique_toolkit.framework_utilities.langchain.client import get_langchain_client  # noqa: F401, I001

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

# You can add other classes you frequently use here as well

__all__ = [
    "LanguageModelService",
    "LanguageModelMessages",
    "LanguageModelName",
    "LanguageModelToolDescription",
    "ChatService",
    "ContentService",
    "EmbeddingService",
    "ShortTermMemoryService",
    "KnowledgeBaseService",
    "get_openai_client",
    "get_async_openai_client",
]

# Add langchain-specific exports if available
if _LANGCHAIN_AVAILABLE:
    __all__.append("get_langchain_client")
