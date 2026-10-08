"""Deprecated import path shim — use the stable module instead."""

from importlib import import_module

from unique_toolkit._common.streaming_deprecation import (
    reexport_streaming_module,
    warn_streaming_deprecated_import,
)

_OLD = "unique_toolkit.experimental.integrations.openai.streaming.event_routing.subscribers.progress_log_persister"
_NEW = "unique_toolkit.integrations.openai.streaming.event_routing.subscribers.progress_log_persister"

warn_streaming_deprecated_import(old_path=_OLD, new_path=_NEW)

reexport_streaming_module(globals(), import_module(_NEW))
