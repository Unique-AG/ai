"""Shared helpers for narrowing LanguageModelName to tenant-available subsets."""

from __future__ import annotations

from enum import StrEnum

from unique_toolkit.language_model.default_language_model import DEFAULT_LANGUAGE_MODEL
from unique_toolkit.language_model.infos import LanguageModelName

NO_MODEL_INTERSECTION_MSG = (
    "No available language models intersect with LanguageModelName."
)


class NoModelIntersectionError(ValueError):
    """Raised when model names do not match any ``LanguageModelName`` member."""

    def __init__(self, models: list[str] | None = None) -> None:
        self.models = list(models or [])
        model_detail = f" models={self.models!r}" if models is not None else ""
        super().__init__(f"{NO_MODEL_INTERSECTION_MSG}{model_detail}")


def intersect_with_language_model_name(models: list[str]) -> dict[str, str]:
    """Return ``{member_name: member_value}`` for models present in *models*.

    Raises:
        ValueError: If none of *models* match a ``LanguageModelName`` member.
    """
    model_set = set(models)
    members = {
        name: member.value
        for name, member in LanguageModelName.__members__.items()
        if name in model_set or member.value in model_set
    }
    if not members:
        raise NoModelIntersectionError(models)
    return members


def build_narrowed_language_model_enum(members: dict[str, str]) -> type[StrEnum]:
    if not members:
        raise NoModelIntersectionError()
    if len(members) == len(LanguageModelName.__members__):
        return LanguageModelName
    return StrEnum("ActiveLanguageModelName", members)


def build_language_model_enum_from_names(models: list[str]) -> type[StrEnum]:
    return build_narrowed_language_model_enum(
        intersect_with_language_model_name(models)
    )


def resolve_default_active_language_model(
    active_models: type[StrEnum],
) -> LanguageModelName:
    """Return the preferred default from a tenant-narrowed (or full) model enum.

    Ranking:
    1. ``DEFAULT_LANGUAGE_MODEL`` when it is in *active_models*
    2. Otherwise the first member in static ``LanguageModelName`` definition order
       that appears in *active_models* (stable, not API response order)
    """
    preferred_name = DEFAULT_LANGUAGE_MODEL.name
    if preferred_name in active_models.__members__:
        return LanguageModelName[preferred_name]

    for name in LanguageModelName.__members__:
        if name in active_models.__members__:
            return LanguageModelName[name]

    return DEFAULT_LANGUAGE_MODEL
