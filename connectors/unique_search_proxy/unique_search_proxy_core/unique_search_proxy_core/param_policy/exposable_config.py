"""Config base for engines carrying ``ExposableParam`` knobs.

Standard search engines and agent engines own the same parameter lifecycle:
partial exposable JSON is merged with the field's ``default_factory`` before
validation, the admin-exposed subset is projected into an LLM-facing model, and
deployment defaults are resolved into a validated request body. That lifecycle
lives here so :class:`~unique_search_proxy_core.search_engines.base.BaseSearchEngineConfig`
and :class:`~unique_search_proxy_core.agent_engines.base.BaseAgentEngineConfig`
share one implementation.

Subclasses supply the two pieces this base cannot know: ``request_model()``
(which request base class the derived body extends) and the
``_exposed_params_model_name`` / ``_merge_exclude_fields`` class vars.
"""

from __future__ import annotations

from typing import Any, ClassVar, Mapping

from pydantic import BaseModel, model_validator

from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.param_policy.derive import derive_exposed_params_model
from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    merge_exposable_params_with_factory_defaults,
)
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams
from unique_search_proxy_core.schema import camelized_model_config

#: Provider discriminator field carried by every engine config.
ENGINE_FIELD = "engine"


class ExposableParamsConfig(BaseModel):
    """Deployment config whose optional knobs may be exposed to the LLM.

    - :meth:`exposed_params_model` — the LLM-facing knobs of this deployment.
    - :meth:`merge` — deployment defaults + LLM overrides -> validated request.
    """

    model_config = camelized_model_config

    #: Name of the derived exposed-params model; set by every concrete config.
    _exposed_params_model_name: ClassVar[str]

    #: Config fields that never contribute a request default in :meth:`merge`.
    #: The discriminator is set from the config itself; engine bases extend this
    #: with their own server-side-only fields (e.g. the agent ``output_schema``).
    _merge_exclude_fields: ClassVar[frozenset[str]] = frozenset({ENGINE_FIELD})

    @model_validator(mode="before")
    @classmethod
    def _merge_exposable_factory_defaults(cls, data: Any) -> Any:
        """Merge exposable knobs with field ``default_factory`` when JSON omits ``value``."""
        return merge_exposable_params_with_factory_defaults(cls, data)

    @classmethod
    def request_model(cls) -> type[BaseModel]:
        """HTTP request body model derived from this config."""
        raise NotImplementedError

    def exposed_params_model(self) -> type[ExposedParams] | None:
        """Plain model class with exactly the knobs this deployment exposed.

        One optional field per config field whose ``ExposableParam`` has
        ``expose=True``: camelCase alias, description-only schema, no admin
        defaults. Returns ``None`` when nothing is exposed. Consumers subclass
        the result (or pass it as an extra base to ``create_model``) to graft
        the knobs onto their own tool-parameter models.

        Example: ``config.exposed_params_model()`` -> ``GoogleExposedParams``.
        """
        return derive_exposed_params_model(
            self,
            name=type(self)._exposed_params_model_name,
        )

    def merge(self, overrides: Mapping[str, Any], *, query: str) -> BaseModel:
        """Deployment defaults + LLM/caller overrides + query -> validated request.

        Defaults: plain fields contribute their value; ``ExposableParam`` knobs
        contribute ``value`` when not ``None`` (deactivated knobs are dropped);
        ``engine`` always comes from this config. ``overrides`` win over
        defaults. Validates into :meth:`request_model`.

        Example: ``config.merge({"date_restrict": "d7"}, query="ai news")``.
        """
        merged: dict[str, Any] = self._merge_defaults()
        merged.update(overrides)
        merged[QUERY_FIELD] = query
        merged[ENGINE_FIELD] = getattr(self, ENGINE_FIELD)
        return type(self).request_model().model_validate(merged)

    def _merge_defaults(self) -> dict[str, Any]:
        """Plain deployment default values (``ExposableParam`` resolved, ``None`` dropped)."""
        defaults: dict[str, Any] = {}
        for field_name in type(self).model_fields:
            if field_name in type(self)._merge_exclude_fields:
                continue
            raw = getattr(self, field_name)
            if isinstance(raw, ExposableParam):
                if raw.value is not None:
                    defaults[field_name] = raw.value
            elif raw is not None:
                defaults[field_name] = raw
        return defaults


__all__ = ["ENGINE_FIELD", "ExposableParamsConfig"]
