"""OpenAI-typed streaming event handler protocols.

This package contains only the **framework-specific** event handler contracts
that reference ``openai.types.*`` payloads. The framework-agnostic
pieces (``TextState``, ``StreamEventHandlerProtocol``, ``TextFlushed``,
``ActivityProgressUpdate``, ``AppendixProducer``, ``UsageProducer``)
live in the domain layer at :mod:`unique_toolkit.experimental.components.streaming` —
import them from there.

* :mod:`chat_completions` — Chat Completions event handler protocols.
* :mod:`responses` — Responses API event handler protocols.
"""

from __future__ import annotations

from .chat_completions import (
    ChatCompletionTextEventHandlerProtocol,
    ChatCompletionToolCallEventHandlerProtocol,
)
from .responses import (
    ResponsesCodeInterpreterEventHandlerProtocol,
    ResponsesCompletedEventHandlerProtocol,
    ResponsesTextDeltaEventHandlerProtocol,
    ResponsesToolCallEventHandlerProtocol,
)

__all__ = [
    "ChatCompletionTextEventHandlerProtocol",
    "ChatCompletionToolCallEventHandlerProtocol",
    "ResponsesCodeInterpreterEventHandlerProtocol",
    "ResponsesCompletedEventHandlerProtocol",
    "ResponsesTextDeltaEventHandlerProtocol",
    "ResponsesToolCallEventHandlerProtocol",
]
