"""Pydantic annotation for narrowing enum JSON schemas without changing validation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic.annotated_handlers import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

E = TypeVar("E", bound=StrEnum)


class RestrictEnum(Generic[E]):
    """Annotation marker that narrows enum values in the JSON schema only.

    Runtime validation still accepts the full enum; pair with a separate
    ``BeforeValidator`` when tenant-scoped enforcement is required.

    Accepts a list of values or a zero-argument callable that returns one::

        color: Annotated[Color, RestrictEnum(["red", "blue"])]
        color: Annotated[Color, RestrictEnum(allowed_colors)]   # callable
    """

    def __init__(
        self,
        allowed: Iterable[E | str] | Callable[[], Iterable[E | str]],
    ) -> None:
        if callable(allowed):
            self._factory: Callable[[], Iterable[E | str]] | None = allowed
            self._raw: tuple[E | str, ...] | None = None
        else:
            self._factory = None
            self._raw = tuple(allowed)
        self._resolved: list[E] | None = None

    def _resolve(self, enum_cls: type[E]) -> list[E]:
        if self._resolved is None:
            if self._raw is not None:
                raw: Iterable[E | str] = self._raw
            elif self._factory is not None:
                raw = self._factory()
            else:
                raise AssertionError(
                    "RestrictEnum has neither raw values nor a factory"
                )
            members: list[E] = []
            for item in raw:
                if isinstance(item, enum_cls):
                    members.append(item)
                else:
                    try:
                        members.append(enum_cls(item))
                    except ValueError:
                        valid = [e.value for e in enum_cls]
                        raise ValueError(
                            f"{item!r} is not a valid value for {enum_cls.__name__}. "
                            f"Expected one of: {valid}"
                        ) from None
            self._resolved = members
        return self._resolved

    def __get_pydantic_json_schema__(
        self,
        core_schema_: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        schema = handler(core_schema_)
        assert self._resolved is not None
        schema["enum"] = [v.value for v in self._resolved]
        schema.pop("title", None)
        return schema

    def __get_pydantic_core_schema__(
        self,
        source_type: type[E],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        self._resolve(source_type)
        return handler(source_type)
