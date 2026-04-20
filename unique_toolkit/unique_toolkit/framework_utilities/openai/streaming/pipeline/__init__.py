"""Streaming pipeline primitives (protocols, handlers, pipelines, events, subscribers).

Layout:
- :mod:`protocols` — package: ``common`` (``TextState``, base protocol), ``chat_completions``, ``responses``.
- :mod:`events` — domain events (``StreamStarted``, ``TextDelta``, ``StreamEnded``) + ``StreamEventBus``.
- :mod:`subscribers` — default bus subscribers (e.g. ``MessagePersistingSubscriber``).
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
from .events import (
    ActivityProgress,
    ActivityStatus,
    StreamEnded,
    StreamEvent,
    StreamEventBus,
    StreamStarted,
    TextDelta,
)
from .protocols import (
    ActivityProgressProducer,
    ActivityProgressUpdate,
    AppendixProducer,
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
from .subscribers import MessagePersistingSubscriber, ProgressLogPersister

__all__ = [
    "ActivityProgress",
    "ActivityProgressProducer",
    "ActivityProgressUpdate",
    "ActivityStatus",
    "AppendixProducer",
    "ChatCompletionStreamPipeline",
    "ChatCompletionTextHandler",
    "ChatCompletionTextHandlerProtocol",
    "ChatCompletionToolCallHandler",
    "ChatCompletionToolCallHandlerProtocol",
    "ChatCompletionsCompleteWithReferences",
    "MessagePersistingSubscriber",
    "ProgressLogPersister",
    "ResponsesCodeInterpreterHandler",
    "ResponsesCodeInterpreterHandlerProtocol",
    "ResponsesCompleteWithReferences",
    "ResponsesCompletedHandler",
    "ResponsesCompletedHandlerProtocol",
    "ResponsesStreamPipeline",
    "ResponsesTextDeltaHandler",
    "ResponsesTextDeltaHandlerProtocol",
    "ResponsesToolCallHandler",
    "ResponsesToolCallHandlerProtocol",
    "StreamEnded",
    "StreamEvent",
    "StreamEventBus",
    "StreamHandlerProtocol",
    "StreamStarted",
    "TextDelta",
    "TextState",
]
