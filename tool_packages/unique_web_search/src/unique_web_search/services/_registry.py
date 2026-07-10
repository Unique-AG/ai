"""Generic self-registration registry for pluggable service implementations."""

from __future__ import annotations

import importlib
import operator
import pkgutil
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from typing import Any, Callable, Generic, Iterable, TypeVar

from pydantic import BaseModel

K = TypeVar("K", bound=Enum)
S = TypeVar("S", bound="BaseSpec[Any]")


@dataclass(frozen=True)
class BaseSpec(Generic[K]):
    """Metadata shared by every registered implementation."""

    name: str
    key: K
    config_cls: type[BaseModel]
    impl_cls: type


class Registry(Generic[K, S]):
    """Collects implementation specs keyed by a discriminator enum value."""

    def __init__(self, spec_cls: type[S]) -> None:
        self._spec_cls = spec_cls
        self._by_key: dict[K, S] = {}

    def register(
        self,
        *,
        name: str,
        key: K,
        config_cls: type[BaseModel],
        **extra: Any,
    ) -> Callable[[type], type]:
        def deco(impl_cls: type) -> type:
            if key in self._by_key:
                raise ValueError(f"{key!r} already registered")
            self._by_key[key] = self._spec_cls(
                name=name,
                key=key,
                config_cls=config_cls,
                impl_cls=impl_cls,
                **extra,
            )
            return impl_cls

        return deco

    @property
    def specs(self) -> tuple[S, ...]:
        return tuple(self._by_key.values())

    def __getitem__(self, key: K) -> S:
        return self._by_key[key]

    def by_name(self) -> dict[str, S]:
        return {spec.name: spec for spec in self._by_key.values()}

    def name_to_config(self) -> dict[str, type[BaseModel]]:
        return {spec.name: spec.config_cls for spec in self._by_key.values()}

    def config_types_from_names(self, names: list[str]) -> type[BaseModel]:
        assert len(names) >= 1, "At least one name must be provided"

        by_name = self.by_name()
        selected_types = [
            by_name[name.lower()].config_cls
            for name in names
            if name.lower() in by_name
        ]
        if not selected_types:
            raise ValueError(f"No config found for names: {names}")
        if len(selected_types) == 1:
            return selected_types[0]
        return reduce(operator.or_, selected_types)

    def default_config(self, names: list[str]) -> type[BaseModel]:
        assert len(names) >= 1, "At least one name must be provided"
        return self.by_name()[names[0].lower()].config_cls

    def autodiscover(
        self,
        path: Iterable[str],
        package: str,
        *,
        exclude: frozenset[str] | set[str] = frozenset(),
    ) -> None:
        for info in pkgutil.iter_modules(path):
            if info.ispkg or info.name.startswith("_") or info.name in exclude:
                continue
            importlib.import_module(f"{package}.{info.name}")

    def assert_enum_coverage(
        self,
        *enums: type[Enum],
        exempt: frozenset[Enum] | set[Enum] = frozenset(),
    ) -> None:
        registered = set(self._by_key.keys())
        for enum_cls in enums:
            for member in enum_cls:
                if member in exempt:
                    continue
                if member not in registered:
                    raise AssertionError(
                        f"{enum_cls.__name__}.{member.name} has no registry entry"
                    )
