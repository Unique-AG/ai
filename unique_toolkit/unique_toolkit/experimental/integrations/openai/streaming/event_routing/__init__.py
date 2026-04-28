"""Streaming event routing primitives (protocols, event handlers, event routing, events, subscribers).

Layout:
- :mod:`protocols` — OpenAI-typed event handler protocols (Chat Completions, Responses).
  Framework-agnostic event handler contracts (``TextState``, ``StreamEventHandlerProtocol``,
  ``TextFlushed``, ``ActivityProgressUpdate``, ``AppendixProducer``,
  ``UsageProducer``) live in the domain layer at
  :mod:`unique_toolkit.experimental.components.streaming`.
- :mod:`events` — domain events (``StreamStarted``, ``TextDelta``, ``StreamEnded``, ``ActivityProgress``) plus ``StreamEventBus`` (routing table of typed channels) and the ``StreamSubscriber`` protocol.
- :mod:`subscribers` — default bus subscribers (e.g. ``MessagePersistingSubscriber``).
- :mod:`chat_completions` — Chat Completions stream (``chat.completions.create``).
- :mod:`responses` — Responses API stream (``responses.create``).
"""

from __future__ import annotations

from unique_toolkit.experimental.components.streaming import (
    ActivityProgressUpdate,
    AppendixProducer,
    StreamEventHandlerProtocol,
    TextFlushed,
    TextState,
    UsageProducer,
)

from .chat_completions import (
    ChatCompletionsCompleteWithReferences,
    ChatCompletionStreamEventRouter,
    ChatCompletionTextEventHandler,
    ChatCompletionToolCallEventHandler,
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
    ChatCompletionTextEventHandlerProtocol,
    ChatCompletionToolCallEventHandlerProtocol,
    ResponsesCodeInterpreterEventHandlerProtocol,
    ResponsesCompletedEventHandlerProtocol,
    ResponsesTextDeltaEventHandlerProtocol,
    ResponsesToolCallEventHandlerProtocol,
)
from .responses import (
    ResponsesCodeInterpreterEventHandler,
    ResponsesCompletedEventHandler,
    ResponsesCompleteWithReferences,
    ResponsesStreamEventRouter,
    ResponsesTextDeltaEventHandler,
    ResponsesToolCallEventHandler,
)
from .subscribers import MessagePersistingSubscriber, ProgressLogPersister

__all__ = [
    "ActivityProgress",
    "ActivityProgressUpdate",
    "ActivityStatus",
    "AppendixProducer",
    "ChatCompletionStreamEventRouter",
    "ChatCompletionTextEventHandler",
    "ChatCompletionTextEventHandlerProtocol",
    "ChatCompletionToolCallEventHandler",
    "ChatCompletionToolCallEventHandlerProtocol",
    "ChatCompletionsCompleteWithReferences",
    "MessagePersistingSubscriber",
    "ProgressLogPersister",
    "ResponsesCodeInterpreterEventHandler",
    "ResponsesCodeInterpreterEventHandlerProtocol",
    "ResponsesCompleteWithReferences",
    "ResponsesCompletedEventHandler",
    "ResponsesCompletedEventHandlerProtocol",
    "ResponsesStreamEventRouter",
    "ResponsesTextDeltaEventHandler",
    "ResponsesTextDeltaEventHandlerProtocol",
    "ResponsesToolCallEventHandler",
    "ResponsesToolCallEventHandlerProtocol",
    "StreamEnded",
    "StreamEvent",
    "StreamEventBus",
    "StreamEventHandlerProtocol",
    "StreamStarted",
    "StreamSubscriber",
    "TextDelta",
    "TextFlushed",
    "TextState",
    "UsageProducer",
]
