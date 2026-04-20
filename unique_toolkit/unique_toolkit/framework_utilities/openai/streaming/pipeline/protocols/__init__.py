"""OpenAI-typed streaming handler protocols.

This package contains only the **framework-specific** handler contracts
that reference ``openai.types.*`` payloads. The framework-agnostic
pieces (``TextState``, ``StreamHandlerProtocol``, ``TextFlushed``,
``ActivityProgressUpdate``, ``AppendixProducer``) live in the domain
layer at :mod:`unique_toolkit.protocols.streaming` — import them from
there.

* :mod:`chat_completions` — Chat Completions handler protocols.
* :mod:`responses` — Responses API handler protocols.
"""

from __future__ import annotations

from .chat_completions import (
    ChatCompletionTextHandlerProtocol,
    ChatCompletionToolCallHandlerProtocol,
)
from .responses import (
    ResponsesCodeInterpreterHandlerProtocol,
    ResponsesCompletedHandlerProtocol,
    ResponsesTextDeltaHandlerProtocol,
    ResponsesToolCallHandlerProtocol,
)

__all__ = [
    "ChatCompletionTextHandlerProtocol",
    "ChatCompletionToolCallHandlerProtocol",
    "ResponsesCodeInterpreterHandlerProtocol",
    "ResponsesCompletedHandlerProtocol",
    "ResponsesTextDeltaHandlerProtocol",
    "ResponsesToolCallHandlerProtocol",
]
