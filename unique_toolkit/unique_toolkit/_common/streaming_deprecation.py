"""Shared deprecation messaging for graduated streaming import paths."""

from __future__ import annotations

import warnings
from types import ModuleType
from typing import Any

STREAMING_DEPRECATED_REMOVAL_DATE = "2026-10-17"

_SKIP_REEXPORT_ATTRS = frozenset(
    {
        "__name__",
        "__doc__",
        "__package__",
        "__loader__",
        "__spec__",
        "__file__",
        "__cached__",
        "__path__",
        "__builtins__",
    }
)


def warn_streaming_deprecated_import(*, old_path: str, new_path: str) -> None:
    """Emit a ``DeprecationWarning`` for a moved streaming import path."""
    warnings.warn(
        f"Importing from {old_path!r} is deprecated. "
        f"Use {new_path!r} instead. "
        f"This import path will be removed on {STREAMING_DEPRECATED_REMOVAL_DATE}.",
        DeprecationWarning,
        stacklevel=2,
    )


def reexport_streaming_module(
    destination: dict[str, Any],
    implementation: ModuleType,
) -> None:
    """Copy stable-module attributes onto a deprecated import shim.

    ``__path__`` is excluded so experimental *package* shims keep their own
    search path. Copying it would make nested imports load the stable source
    files under the old module name, producing duplicate class objects.

    Args:
        destination (dict[str, Any]): The shim module's ``globals()``.
        implementation (ModuleType): The stable module being re-exported.
    """
    for name, value in implementation.__dict__.items():
        if name in _SKIP_REEXPORT_ATTRS:
            continue
        destination[name] = value
