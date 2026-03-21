"""unique_client — OOP wrapper around the Unique SDK.

Usage::

    from unique_client import UniqueClient

    client = UniqueClient(
        user_id="usr_...",
        company_id="cmp_...",
        api_key="ukey_...",   # optional if already set on unique_sdk
        app_id="app_...",     # optional if already set on unique_sdk
    )

    # Async usage
    msg = await client.messages.create(...)
    await msg.modify(text="Updated")
    await msg.delete(chatId="chat_123")
"""

from ._base import BaseManager, DomainObject
from ._client import UniqueClient
from .resources import (
    AgenticTableCellObject,
    AgenticTableManager,
    AgenticTableSheetObject,
    AcronymsManager,
    AcronymsObject,
    ChatCompletionManager,
    ChatCompletionResult,
    ContentManager,
    ContentObject,
    ElicitationManager,
    ElicitationObject,
    EmbeddingsManager,
    EmbeddingsResult,
    FolderManager,
    FolderObject,
    GroupManager,
    GroupObject,
    IntegratedManager,
    MCPManager,
    MCPResult,
    MemoryManager,
    MemoryObject,
    MessageAssessmentManager,
    MessageAssessmentObject,
    MessageExecutionManager,
    MessageExecutionObject,
    MessageLogManager,
    MessageLogObject,
    MessageManager,
    MessageObject,
    MessageToolManager,
    MessageToolObject,
    ModelsManager,
    ResponsesStreamResult,
    SearchManager,
    SearchResult,
    SearchStringManager,
    SearchStringResult,
    SpaceManager,
    SpaceObject,
    StreamCompletionResult,
    UserManager,
    UserObject,
)

__all__ = [
    # Main entry point
    "UniqueClient",
    # Base
    "DomainObject",
    "BaseManager",
    # Message family
    "MessageManager",
    "MessageObject",
    "MessageLogManager",
    "MessageLogObject",
    "MessageToolManager",
    "MessageToolObject",
    "MessageAssessmentManager",
    "MessageAssessmentObject",
    "MessageExecutionManager",
    "MessageExecutionObject",
    # Content & search
    "ContentManager",
    "ContentObject",
    "SearchManager",
    "SearchResult",
    "SearchStringManager",
    "SearchStringResult",
    "EmbeddingsManager",
    "EmbeddingsResult",
    # Space
    "SpaceManager",
    "SpaceObject",
    # Folder
    "FolderManager",
    "FolderObject",
    # Completions
    "ChatCompletionManager",
    "ChatCompletionResult",
    "IntegratedManager",
    "StreamCompletionResult",
    "ResponsesStreamResult",
    # Users & groups
    "UserManager",
    "UserObject",
    "GroupManager",
    "GroupObject",
    # Memory
    "MemoryManager",
    "MemoryObject",
    # Elicitation
    "ElicitationManager",
    "ElicitationObject",
    # Agentic table
    "AgenticTableManager",
    "AgenticTableCellObject",
    "AgenticTableSheetObject",
    # Misc
    "ModelsManager",
    "AcronymsManager",
    "AcronymsObject",
    "MCPManager",
    "MCPResult",
]
