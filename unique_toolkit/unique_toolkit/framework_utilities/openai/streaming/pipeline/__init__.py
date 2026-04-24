"""Streaming pipeline primitives (protocols, handlers, pipelines, events, subscribers).

Layout:
- :mod:`protocols` — OpenAI-typed handler protocols (Chat Completions, Responses).
  Framework-agnostic handler contracts (``TextState``, ``StreamHandlerProtocol``,
  ``TextFlushed``, ``ActivityProgressUpdate``, ``AppendixProducer``) live in
  the domain layer at :mod:`unique_toolkit.protocols.streaming`.
- :mod:`events` — domain events (``StreamStarted``, ``TextDelta``, ``StreamEnded``, ``ActivityProgress``) plus ``StreamEventBus`` (routing table of typed channels) and the ``StreamSubscriber`` protocol.
- :mod:`subscribers` — default bus subscribers (e.g. ``MessagePersistingSubscriber``).
- :mod:`chat_completions` — Chat Completions stream (``chat.completions.create``).
- :mod:`responses` — Responses API stream (``responses.create``).
"""

from __future__ import annotations

from unique_toolkit.protocols.streaming import (
    ActivityProgressUpdate,
    AppendixProducer,
    StreamHandlerProtocol,
    TextFlushed,
    TextState,
)

from .chat_completions import (
    ChatCompletionsCompleteWithReferences,
    ChatCompletionStreamEventRouter,
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
    StreamSubscriber,
    TextDelta,
)
from .protocols import (
    ChatCompletionTextHandlerProtocol,
    ChatCompletionToolCallHandlerProtocol,
    ResponsesCodeInterpreterHandlerProtocol,
    ResponsesCompletedHandlerProtocol,
    ResponsesTextDeltaHandlerProtocol,
    ResponsesToolCallHandlerProtocol,
)
from .responses import (
    ResponsesCodeInterpreterHandler,
    ResponsesCompletedHandler,
    ResponsesCompleteWithReferences,
    ResponsesStreamEventRouter,
    ResponsesTextDeltaHandler,
    ResponsesToolCallHandler,
)
from .subscribers import MessagePersistingSubscriber, ProgressLogPersister

__all__ = [
    "ActivityProgress",
    "ActivityProgressUpdate",
    "ActivityStatus",
    "AppendixProducer",
    "ChatCompletionStreamEventRouter",
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
    "ResponsesStreamEventRouter",
    "ResponsesTextDeltaHandler",
    "ResponsesTextDeltaHandlerProtocol",
    "ResponsesToolCallHandler",
    "ResponsesToolCallHandlerProtocol",
    "StreamEnded",
    "StreamEvent",
    "StreamEventBus",
    "StreamHandlerProtocol",
    "StreamStarted",
    "StreamSubscriber",
    "TextDelta",
    "TextFlushed",
    "TextState",
]
