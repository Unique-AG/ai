"""Redirect deprecated import paths to stable modules."""

from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass
from importlib import import_module
from importlib.abc import MetaPathFinder
from importlib.util import spec_from_loader
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec


@dataclass(frozen=True, slots=True)
class DeprecatedImportMapping:
    """Map a deprecated import prefix to its stable replacement."""

    old_prefix: str
    new_prefix: str
    removal_date: str


_DEPRECATED_IMPORT_MAPPINGS: list[DeprecatedImportMapping] = []


def register_deprecated_import_mapping(mapping: DeprecatedImportMapping) -> None:
    """Register a deprecated import prefix redirect."""
    _DEPRECATED_IMPORT_MAPPINGS.append(mapping)


def warn_deprecated_import(*, old_path: str, new_path: str, removal_date: str) -> None:
    """Emit a ``DeprecationWarning`` for a moved import path."""
    warnings.warn(
        f"Importing from {old_path!r} is deprecated. "
        f"Use {new_path!r} instead. "
        f"This import path will be removed on {removal_date}.",
        DeprecationWarning,
        stacklevel=2,
    )


def _resolve_stable_module_name(module_name: str) -> DeprecatedImportMapping | None:
    for mapping in _DEPRECATED_IMPORT_MAPPINGS:
        if module_name == mapping.old_prefix or module_name.startswith(
            f"{mapping.old_prefix}."
        ):
            return mapping
    return None


class _DeprecatedImportLoader:
    """Load a stable module under a deprecated import name."""

    def __init__(
        self,
        old_name: str,
        new_name: str,
        removal_date: str,
    ) -> None:
        self._old_name = old_name
        self._new_name = new_name
        self._removal_date = removal_date

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        warn_deprecated_import(
            old_path=self._old_name,
            new_path=self._new_name,
            removal_date=self._removal_date,
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


class _DeprecatedImportFinder(MetaPathFinder):
    """Resolve registered deprecated imports to stable modules."""

    def find_spec(
        self,
        fullname: str,
        path: object | None = None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        mapping = _resolve_stable_module_name(fullname)
        if mapping is None:
            return None
        stable_name = mapping.new_prefix + fullname[len(mapping.old_prefix) :]
        loader = _DeprecatedImportLoader(
            fullname,
            stable_name,
            mapping.removal_date,
        )
        return spec_from_loader(fullname, loader)


def install_deprecated_import_redirect() -> None:
    """Register the deprecated import redirect finder once."""
    if any(isinstance(finder, _DeprecatedImportFinder) for finder in sys.meta_path):
        return
    sys.meta_path.insert(0, _DeprecatedImportFinder())
