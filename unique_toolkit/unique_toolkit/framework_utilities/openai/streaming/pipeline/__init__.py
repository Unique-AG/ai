"""Streaming pipeline primitives (protocols, handlers, pipelines).

Layout:
- :mod:`protocols` — package: ``common`` (``TextState``, base protocol), ``chat_completions``, ``responses``.
- :mod:`chat_completions` — Chat Completions stream (``chat.completions.create``).
- :mod:`responses` — Responses API stream (``responses.create``).
"""

from __future__ import annotations

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
    TextState,
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
    # --- Shared types ---
    "TextState",
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
]
