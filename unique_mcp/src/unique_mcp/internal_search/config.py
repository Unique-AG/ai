from __future__ import annotations

from pydantic import BaseModel, Field
from unique_toolkit.components.internal_search import (
    InternalSearchConfig,
    KnowledgeBaseInternalSearchConfig,
)

from unique_mcp.context_requirements import ContextRequirements, merge_tool_meta
from unique_mcp.internal_search.meta import SearchMetaKeys
from unique_mcp.meta_keys import MetaKeys

DEFAULT_SEARCH_STRING_DESCRIPTION = (
    "The search string, or list of search strings, used to retrieve relevant "
    "internal search results."
)


_CHAT_CONTEXT_REQUIREMENTS = ContextRequirements(
    required=[
        MetaKeys.USER_ID,
        MetaKeys.COMPANY_ID,
        MetaKeys.CHAT_ID,
    ],
    optional=[
        MetaKeys.USER_MESSAGE_ID,
        MetaKeys.ASSISTANT_ID,
        MetaKeys.PARENT_CHAT_ID,
        MetaKeys.LAST_ASSISTANT_MESSAGE_ID,
        MetaKeys.LAST_USER_MESSAGE_TEXT,
        SearchMetaKeys.CONTENT_IDS,
        SearchMetaKeys.SELECTED_UPLOADED_FILE_IDS,
        SearchMetaKeys.METADATA_FILTER,
        SearchMetaKeys.LANGUAGE_MODEL_MAX_INPUT_TOKENS,
    ],
)


_KNOWLEDGE_BASE_CONTEXT_REQUIREMENTS = ContextRequirements(
    required=[
        MetaKeys.USER_ID,
        MetaKeys.COMPANY_ID,
    ],
    optional=[
        SearchMetaKeys.CONTENT_IDS,
        SearchMetaKeys.METADATA_FILTER,
        SearchMetaKeys.LANGUAGE_MODEL_MAX_INPUT_TOKENS,
    ],
)


class BaseInternalSearchMcpConfig(BaseModel):
    name: str = Field(description="Registered MCP tool name.")
    description: str = Field(description="Tool description exposed to MCP clients.")
    param_description_search_string: str = Field(
        default=DEFAULT_SEARCH_STRING_DESCRIPTION,
        description="Description of the MCP tool's search_string argument.",
    )
    no_results_message: str = Field(
        default="No internal search results found.",
        description="Fallback text returned when the search yields no chunks.",
    )
    tool_meta: dict[str, object] = Field(
        default_factory=dict,
        description="Additional MCP tool metadata exposed during registration.",
    )


class ChatInternalSearchMcpConfig(BaseInternalSearchMcpConfig):
    name: str = Field(
        default="chat-internal-search",
        description="Registered MCP tool name.",
    )
    description: str = Field(
        default=(
            "Search files and content already available in the current chat context."
        ),
        description="Tool description exposed to MCP clients.",
    )
    no_results_message: str = Field(
        default="No relevant chat files or chat-scoped content were found.",
        description="Fallback text returned when the search yields no chunks.",
    )
    tool_meta: dict[str, object] = Field(
        default_factory=lambda: merge_tool_meta(None, _CHAT_CONTEXT_REQUIREMENTS),
        description=(
            "Additional MCP tool metadata exposed during registration. Defaults "
            "to a `unique.app/context-requirements` declaration covering the "
            "chat-scoped request `_meta` keys the tool consumes."
        ),
    )
    execution_config: InternalSearchConfig = Field(
        default_factory=InternalSearchConfig,
        description="Runtime configuration forwarded to ChatInternalSearchService.",
    )


class KnowledgeBaseInternalSearchMcpConfig(BaseInternalSearchMcpConfig):
    name: str = Field(
        default="kb-internal-search",
        description="Registered MCP tool name.",
    )
    description: str = Field(
        default="Search the configured Unique Knowledge Base for relevant content.",
        description="Tool description exposed to MCP clients.",
    )
    no_results_message: str = Field(
        default="No relevant Knowledge Base content was found.",
        description="Fallback text returned when the search yields no chunks.",
    )
    tool_meta: dict[str, object] = Field(
        default_factory=lambda: merge_tool_meta(
            None, _KNOWLEDGE_BASE_CONTEXT_REQUIREMENTS
        ),
        description=(
            "Additional MCP tool metadata exposed during registration. Defaults "
            "to a `unique.app/context-requirements` declaration covering the "
            "auth + search-scoping keys the knowledge-base tool consumes."
        ),
    )
    execution_config: KnowledgeBaseInternalSearchConfig = Field(
        default_factory=KnowledgeBaseInternalSearchConfig,
        description=(
            "Runtime configuration forwarded to KnowledgeBaseInternalSearchService."
        ),
    )


__all__ = [
    "BaseInternalSearchMcpConfig",
    "ChatInternalSearchMcpConfig",
    "KnowledgeBaseInternalSearchMcpConfig",
    "DEFAULT_SEARCH_STRING_DESCRIPTION",
]
