"""RJSF tags for deployment knobs the environment has taken out of admin hands."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from unique_toolkit._common.pydantic.rjsf_tags import DynamicRJSFTag, RJSFMetaTag

_ENFORCED_HELP = "This parameter has been enforced by the infra team."


def enforced_by_infra(enforced: bool, *, help: str | None = None) -> RJSFMetaTag:
    """Grey out a whole config field (including every child of an ``ExposableParam``).

    Apply to the *field* annotation, not the ``ExposableParam`` type argument:
    ``Annotated[ExposableMarket, DynamicRJSFTag(enforced_by_infra_factory)]``.
    Tags inside ``ExposableParam[Annotated[T, ...]]`` are dropped, because
    ``ui_schema_for_model`` resolves annotations with ``get_type_hints``, which
    does not substitute TypeVars on Pydantic generics.

    Prefer wrapping the factory in :class:`DynamicRJSFTag` so env-driven locks
    are re-evaluated whenever the admin UI schema is generated.
    """
    attrs: dict[str, Any] = {"ui:disabled": enforced}
    if enforced:
        attrs["ui:help"] = help or _ENFORCED_HELP
    return RJSFMetaTag(attrs)


def dynamic_enforced_by_infra(
    factory: Callable[[], bool],
    *,
    help: str | None = None,
) -> DynamicRJSFTag:
    """Like :func:`enforced_by_infra`, but re-reads ``factory()`` at uiSchema time."""

    def _tag() -> RJSFMetaTag:
        return enforced_by_infra(factory(), help=help)

    return DynamicRJSFTag(_tag)
