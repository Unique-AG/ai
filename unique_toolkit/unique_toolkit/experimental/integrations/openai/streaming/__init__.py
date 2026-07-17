"""Deprecated import path shim — use the stable module instead."""

from importlib import import_module

from unique_toolkit._common.streaming_deprecation import (
    warn_streaming_deprecated_import,
)

_OLD = "unique_toolkit.experimental.integrations.openai.streaming"
_NEW = "unique_toolkit.integrations.openai.streaming"

warn_streaming_deprecated_import(old_path=_OLD, new_path=_NEW)

_impl = import_module(_NEW)
for _name, _value in _impl.__dict__.items():
    if _name in {
        "__name__",
        "__doc__",
        "__package__",
        "__loader__",
        "__spec__",
        "__file__",
        "__cached__",
    }:
        continue
    globals()[_name] = _value
