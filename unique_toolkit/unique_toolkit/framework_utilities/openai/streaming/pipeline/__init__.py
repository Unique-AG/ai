"""Streaming pipeline primitives (protocols, handlers, pipelines).

Layout:
- :mod:`protocols` — shared handler protocols (Chat Completions + Responses).
- :mod:`chat_completions` — Chat Completions stream (``chat.completions.create``).
- :mod:`responses` — Responses API stream (``responses.create``).
"""

from __future__ import annotations

from unique_toolkit.framework_utilities.openai.streaming.reference_replacer import (
    ReferenceResolutionReplacer,
)

from .chat_completions import (
    ChatCompletionsCompleteWithReferences,
    ChatCompletionStreamPipeline,
    ChatCompletionTextHandler,
    ChatCompletionToolCallHandler,
)
from .protocols import (
    ChatCompletionTextHandlerProtocol,
    ChatCompletionToolCallHandlerProtocol,
    ResponsesCodeInterpreterHandlerProtocol,
    ResponsesCompletedHandlerProtocol,
    ResponsesTextDeltaHandlerProtocol,
    ResponsesToolCallHandlerProtocol,
    StreamHandlerProtocol,
)
from .responses import (
    ResponsesCodeInterpreterHandler,
    ResponsesCompletedHandler,
    ResponsesCompleteWithReferences,
    ResponsesStreamPipeline,
    ResponsesTextDeltaHandler,
    ResponsesToolCallHandler,
)

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
