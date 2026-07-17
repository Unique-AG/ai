"""Redirect deprecated experimental streaming import paths to stable modules."""

from __future__ import annotations

import sys
import warnings
from importlib import import_module
from importlib.abc import MetaPathFinder
from importlib.util import spec_from_loader
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec

STREAMING_DEPRECATED_REMOVAL_DATE = "2026-10-17"

_DEPRECATED_PREFIX_TO_STABLE = (
    (
        "unique_toolkit.experimental._internal.streaming",
        "unique_toolkit._internal.streaming",
    ),
    (
        "unique_toolkit.experimental.integrations.openai.streaming",
        "unique_toolkit.integrations.openai.streaming",
    ),
)


def _resolve_stable_module_name(module_name: str) -> str | None:
    for old_prefix, new_prefix in _DEPRECATED_PREFIX_TO_STABLE:
        if module_name == old_prefix or module_name.startswith(f"{old_prefix}."):
            return new_prefix + module_name[len(old_prefix) :]
    return None


def warn_streaming_deprecated_import(*, old_path: str, new_path: str) -> None:
    """Emit a ``DeprecationWarning`` for a moved streaming import path."""
    warnings.warn(
        f"Importing from {old_path!r} is deprecated. "
        f"Use {new_path!r} instead. "
        f"This import path will be removed on {STREAMING_DEPRECATED_REMOVAL_DATE}.",
        DeprecationWarning,
        stacklevel=2,
    )


class _DeprecatedStreamingLoader:
    """Load a stable streaming module under a deprecated import name."""

    def __init__(self, old_name: str, new_name: str) -> None:
        self._old_name = old_name
        self._new_name = new_name

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        warn_streaming_deprecated_import(
            old_path=self._old_name, new_path=self._new_name
        )
        target = import_module(self._new_name)
        module.__dict__.update(
            {
                key: value
                for key, value in target.__dict__.items()
                if key
                not in {
                    "__name__",
                    "__doc__",
                    "__package__",
                    "__loader__",
                    "__spec__",
                    "__file__",
                    "__cached__",
                }
            }
        )
        module.__package__ = self._old_name.rpartition(".")[0]


class _DeprecatedStreamingFinder(MetaPathFinder):
    """Resolve deprecated experimental streaming imports to stable modules."""

    def find_spec(
        self,
        fullname: str,
        path: object | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        stable_name = _resolve_stable_module_name(fullname)
        if stable_name is None:
            return None
        loader = _DeprecatedStreamingLoader(fullname, stable_name)
        return spec_from_loader(fullname, loader)


def install_deprecated_streaming_import_redirect() -> None:
    """Register the deprecated streaming import redirect once."""
    if any(isinstance(finder, _DeprecatedStreamingFinder) for finder in sys.meta_path):
        return
    sys.meta_path.insert(0, _DeprecatedStreamingFinder())
