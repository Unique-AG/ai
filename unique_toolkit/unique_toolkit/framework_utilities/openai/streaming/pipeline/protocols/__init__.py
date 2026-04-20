"""Streaming pipeline protocols.

* :mod:`common` — :class:`TextState` and :class:`StreamHandlerProtocol` (shared by all APIs).
* :mod:`responses` — Responses API handler protocols.
* :mod:`chat_completions` — Chat Completions handler protocols.

Import from this package for a flat surface (same names as before) or from submodules
for API-scoped imports.
"""

from __future__ import annotations

from .chat_completions import (
    ChatCompletionTextHandlerProtocol,
    ChatCompletionToolCallHandlerProtocol,
)
from .common import (
    ActivityProgressProducer,
    ActivityProgressUpdate,
    AppendixProducer,
    StreamHandlerProtocol,
    TextState,
)
from .responses import (
    ResponsesCodeInterpreterHandlerProtocol,
    ResponsesCompletedHandlerProtocol,
    ResponsesTextDeltaHandlerProtocol,
    ResponsesToolCallHandlerProtocol,
)

__all__ = [
    "ActivityProgressProducer",
    "ActivityProgressUpdate",
    "AppendixProducer",
    "ChatCompletionTextHandlerProtocol",
    "ChatCompletionToolCallHandlerProtocol",
    "ResponsesCodeInterpreterHandlerProtocol",
    "ResponsesCompletedHandlerProtocol",
    "ResponsesTextDeltaHandlerProtocol",
    "ResponsesToolCallHandlerProtocol",
    "StreamHandlerProtocol",
    "TextState",
]
