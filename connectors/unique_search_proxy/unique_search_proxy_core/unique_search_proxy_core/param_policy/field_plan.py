"""One field plan per config field, computed once and shared by every surface.

``field_plan(config_cls)`` walks a deployment-config model exactly once and
returns the resolved facts each derived surface needs (HTTP request body, LLM
call schema, tool JSON schema): the Python name, the camelCase alias shown to
callers, the plain inner value type, and whether the field is an
``ExposableParam`` knob. Surfaces read this instead of re-walking ``model_fields``
and re-deriving names/annotations independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic.alias_generators import to_camel
from pydantic.fields import FieldInfo

from unique_search_proxy_core.param_policy.annotations import (
    Annotation,
    plain_inner_type,
)
from unique_search_proxy_core.param_policy.exposable_param import (
    is_exposable_param_type,
)


@dataclass(frozen=True)
class FieldPlan:
    """Resolved facts for one config field, shared across every derived surface.

    - ``name``: snake_case Python attribute on the config/request model.
    - ``alias``: camelCase property name shown to HTTP/LLM callers.
    - ``info``: the original config ``FieldInfo`` (title/description/constraints).
    - ``inner_type``: plain value type (``ExposableParam``/``Annotated``/
      ``DeactivatedNone`` stripped; explicit ``| None`` preserved).
    - ``exposable``: whether the field is an ``ExposableParam`` knob.
    """

    name: str
    alias: str
    info: FieldInfo
    inner_type: Annotation
    exposable: bool

    @property
    def description(self) -> str:
        """Admin-authored description, falling back to the field name."""
        return self.info.description or self.name


@lru_cache(maxsize=64)
def field_plan(config_cls: type) -> tuple[FieldPlan, ...]:
    """Resolve every config field once (cached per config class)."""
    plans: list[FieldPlan] = []
    for name, info in config_cls.model_fields.items():
        plans.append(
            FieldPlan(
                name=name,
                alias=info.alias or to_camel(name),
                info=info,
                inner_type=plain_inner_type(info.annotation),
                exposable=is_exposable_param_type(info.annotation),
            ),
        )
    return tuple(plans)


__all__ = ["FieldPlan", "field_plan"]
