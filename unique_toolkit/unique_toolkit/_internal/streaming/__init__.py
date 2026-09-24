"""Framework-agnostic streaming components.

This subpackage exposes streaming behaviour that is useful beyond a single
third-party framework: event handler contracts, text state payloads, citation
normalisation, and other provider-neutral primitives. Concrete framework
adapters live under :mod:`unique_toolkit.integrations`.
"""

from __future__ import annotations

from .common import (
    ActivityProducer,
    ActivityProgressUpdate,
    ActivityStatus,
    AppendixProducer,
    StreamEventHandlerProtocol,
    StreamTextEventHandlerProtocol,
    StreamToolCallEventHandlerProtocol,
    TextFlushed,
    TextState,
    UsageProducer,
)

__all__ = [
    "ActivityProducer",
    "ActivityProgressUpdate",
    "ActivityStatus",
    "AppendixProducer",
    "StreamEventHandlerProtocol",
    "StreamTextEventHandlerProtocol",
    "StreamToolCallEventHandlerProtocol",
    "TextFlushed",
    "TextState",
    "UsageProducer",
]
