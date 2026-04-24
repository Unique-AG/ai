"""Framework-agnostic streaming protocols.

This subpackage exposes the **domain-level** streaming handler contracts
that any framework adapter (OpenAI today, others tomorrow) can realize.
Concrete, framework-typed handler protocols (e.g. the ones referencing
``openai.types``) remain next to their implementations under
``unique_toolkit.framework_utilities``.
"""

from __future__ import annotations

from .common import (
    ActivityProducer,
    ActivityProgressUpdate,
    ActivityStatus,
    AppendixProducer,
    StreamHandlerProtocol,
    StreamTextHandlerProtocol,
    StreamToolCallHandlerProtocol,
    TextFlushed,
    TextState,
)

__all__ = [
    "ActivityProducer",
    "ActivityProgressUpdate",
    "ActivityStatus",
    "AppendixProducer",
    "StreamHandlerProtocol",
    "StreamTextHandlerProtocol",
    "StreamToolCallHandlerProtocol",
    "TextFlushed",
    "TextState",
]
