"""Streaming pipeline primitives (protocols, handlers, pipelines)."""

from __future__ import annotations

from unique_toolkit.framework_utilities.openai.streaming.reference_replacer import (
    ReferenceResolutionReplacer,
)

from .chat_completion_pipeline import ChatCompletionStreamPipeline
from .chat_completion_streaming_handler import ChatCompletionsCompleteWithReferences
from .chat_completion_text_handler import ChatCompletionTextHandler
from .chat_completion_tool_call_handler import ChatCompletionToolCallHandler
from .protocols import (
    ChatCompletionTextHandlerProtocol,
    ChatCompletionToolCallHandlerProtocol,
    ResponsesCodeInterpreterHandlerProtocol,
    ResponsesCompletedHandlerProtocol,
    ResponsesTextDeltaHandlerProtocol,
    ResponsesToolCallHandlerProtocol,
    StreamHandlerProtocol,
)
from .responses_code_interpreter_handler import ResponsesCodeInterpreterHandler
from .responses_completed_handler import ResponsesCompletedHandler
from .responses_pipeline import ResponsesStreamPipeline
from .responses_streaming_handler import ResponsesCompleteWithReferences
from .responses_text_delta_handler import ResponsesTextDeltaHandler
from .responses_tool_call_handler import ResponsesToolCallHandler

__all__ = [
    # --- Pipeline classes ---
    "ChatCompletionStreamPipeline",
    "ResponsesStreamPipeline",
    # --- Handler protocols ---
    "StreamHandlerProtocol",
    "ChatCompletionTextHandlerProtocol",
    "ChatCompletionToolCallHandlerProtocol",
    "ResponsesTextDeltaHandlerProtocol",
    "ResponsesToolCallHandlerProtocol",
    "ResponsesCompletedHandlerProtocol",
    "ResponsesCodeInterpreterHandlerProtocol",
    # --- Handler implementations ---
    "ChatCompletionTextHandler",
    "ChatCompletionToolCallHandler",
    "ResponsesTextDeltaHandler",
    "ResponsesToolCallHandler",
    "ResponsesCompletedHandler",
    "ResponsesCodeInterpreterHandler",
    # --- Streaming handlers (public API) ---
    "ChatCompletionsCompleteWithReferences",
    "ResponsesCompleteWithReferences",
    # --- Replacers ---
    "ReferenceResolutionReplacer",
]
