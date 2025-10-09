"""
DEPRECATED: This module is maintained for backward compatibility only.

Please import from `unique_toolkit.services.chat_service` instead:
    from unique_toolkit.services.chat_service import ChatService

All imports from this module will continue to work but may be removed in a future version.
"""

import warnings

from unique_toolkit.chat.constants import (
    DEFAULT_MAX_MESSAGES,
    DEFAULT_PERCENT_OF_MAX_TOKENS,
    DOMAIN_NAME,
)
from unique_toolkit.chat.deprecated.service import ChatServiceDeprecated
from unique_toolkit.chat.functions import (
    create_message,
    create_message_assessment,
    create_message_assessment_async,
    create_message_async,
    create_message_execution,
    create_message_execution_async,
    create_message_log,
    create_message_log_async,
    get_full_history,
    get_full_history_async,
    get_message_execution,
    get_message_execution_async,
    get_selection_from_history,
    modify_message,
    modify_message_assessment,
    modify_message_assessment_async,
    modify_message_async,
    stream_complete_with_references,
    stream_complete_with_references_async,
    update_message_execution,
    update_message_execution_async,
    update_message_log,
    update_message_log_async,
)
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageAssessment,
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
    ChatMessageRole,
    MessageExecution,
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLog,
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.content.functions import (
    download_content_to_bytes,
    search_contents,
    upload_content_from_bytes,
)
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentReference,
)
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)
from unique_toolkit.language_model.infos import (
    LanguageModelName,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
    LanguageModelToolDescription,
)
from unique_toolkit.services.chat_service import ChatService

warnings.warn(
    "Importing from 'unique_toolkit.chat.service' is deprecated. "
    "Please import from 'unique_toolkit.services.chat_service' instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=1,
)

__all__ = [
    # Main Service Class
    "ChatService",
    "ChatServiceDeprecated",
    # Chat Functions
    "create_message",
    "create_message_assessment",
    "create_message_assessment_async",
    "create_message_async",
    "create_message_execution",
    "create_message_execution_async",
    "create_message_log",
    "create_message_log_async",
    "get_full_history",
    "get_full_history_async",
    "get_message_execution",
    "get_message_execution_async",
    "get_selection_from_history",
    "modify_message",
    "modify_message_assessment",
    "modify_message_assessment_async",
    "modify_message_async",
    "stream_complete_with_references",
    "stream_complete_with_references_async",
    "update_message_execution",
    "update_message_execution_async",
    "update_message_log",
    "update_message_log_async",
    # Chat Constants
    "DEFAULT_MAX_MESSAGES",
    "DEFAULT_PERCENT_OF_MAX_TOKENS",
    "DOMAIN_NAME",
    # Chat Schemas
    "ChatMessage",
    "ChatMessageAssessment",
    "ChatMessageAssessmentLabel",
    "ChatMessageAssessmentStatus",
    "ChatMessageAssessmentType",
    "ChatMessageRole",
    "MessageExecution",
    "MessageExecutionType",
    "MessageExecutionUpdateStatus",
    "MessageLog",
    "MessageLogDetails",
    "MessageLogStatus",
    "MessageLogUncitedReferences",
    # Content Functions
    "download_content_to_bytes",
    "search_contents",
    "upload_content_from_bytes",
    # Content Schemas
    "Content",
    "ContentChunk",
    "ContentReference",
    # Language Model Constants
    "DEFAULT_COMPLETE_TEMPERATURE",
    "DEFAULT_COMPLETE_TIMEOUT",
    # Language Model Infos
    "LanguageModelName",
    # Language Model Schemas
    "LanguageModelMessages",
    "LanguageModelResponse",
    "LanguageModelStreamResponse",
    "LanguageModelTool",
    "LanguageModelToolDescription",
]
