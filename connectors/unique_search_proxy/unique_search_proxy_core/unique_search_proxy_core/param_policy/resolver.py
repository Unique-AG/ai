"""Single orchestrator for config -> request/call-schema/value resolution.

``ConfigRequestResolver`` owns deriving every model surface from one deployment
config: the HTTP request body (``request_model`` / ``agent_request_model`` /
``crawl_request_model``), the deployment default values (``resolve_values``), the
set of LLM-exposed fields (``exposed_field_names``), and the LLM call schema
(``call_schema``). Search-engine-specific concerns (runtime merge, provider query
string) live on :class:`BaseSearchEngineConfig`.

Every request model is built the same way: config fields (with ``ExposableParam``
unwrapped to plain types via :func:`field_plan`) plus the required leading field
(``query`` for search/agent, ``urls`` for crawl) supplied by the shared request
base classes.
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, TypeVar, cast

from pydantic import BaseModel, create_model

from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.param_policy.annotations import (
    Annotation,
    as_optional,
    as_required,
    field_definition_from_info,
    resolve_field_name,
)
from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    is_exposable_param_field,
)
from unique_search_proxy_core.param_policy.field_plan import field_plan
from unique_search_proxy_core.param_policy.request_base import (
    AgentRequestBase,
    CrawlRequestBase,
    SearchRequestBase,
)
from unique_search_proxy_core.schema import camelized_model_config

_AGENT_EXCLUDED = frozenset({"output_schema"})

ConfigT = TypeVar("ConfigT", bound=BaseModel)


def _search_request_model_name(config_cls: type[BaseModel], *, agent: bool) -> str:
    base = config_cls.__name__.removesuffix("Config")
    if agent and not base.endswith("Agent"):
        return f"{base}AgentSearchRequest"
    return f"{base}SearchRequest"


def _build_model(
    config_cls: type[BaseModel],
    *,
    name: str,
    base: type[BaseModel],
    unwrap: bool,
    exclude: frozenset[str],
) -> type[BaseModel]:
    """Derive a request model from a config class (leading field supplied by ``base``)."""
    fields: dict[str, tuple[Any, Any]] = {}
    for plan in field_plan(config_cls):
        if plan.name in exclude:
            continue
        annotation = (
            as_optional(plan.inner_type) if plan.exposable else plan.inner_type
        )
        fields[plan.name] = field_definition_from_info(
            plan.info,
            annotation=annotation,
            force_default_none=unwrap and plan.exposable,
        )
    model = create_model(
        name,
        __base__=base,
        **cast(Any, fields),
    )
    config_module = importlib.import_module(config_cls.__module__)
    model.model_rebuild(_types_namespace=dict(vars(config_module)))
    return model


def _project(
    call_schema: type[BaseModel],
    field_definitions: dict[str, tuple[Any, Any]],
) -> type[BaseModel]:
    """Build the LLM projection model, reusing the source schema's config."""
    model_config = call_schema.model_config or camelized_model_config
    return create_model(
        f"{call_schema.__name__}LlmProjection",
        __config__=model_config,
        **cast(Any, field_definitions),
    )


def project_strict(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
) -> type[BaseModel]:
    """Strict LLM projection: exposed fields are required and never nullable."""
    if not exposed_fields:
        raise ValueError("exposed_fields must contain at least one field name")

    field_definitions: dict[str, tuple[Any, Any]] = {}
    for exposed_name in exposed_fields:
        field_name = resolve_field_name(call_schema, exposed_name)
        field_info = call_schema.model_fields[field_name]
        field_definitions[field_name] = field_definition_from_info(
            field_info,
            annotation=as_required(field_info.annotation),
            strict_required=True,
        )
    return _project(call_schema, field_definitions)


def project_non_strict(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
    *,
    field_defaults: dict[str, Any] | None = None,
    field_annotations: dict[str, Annotation] | None = None,
) -> type[BaseModel]:
    """Non-strict LLM projection: exposed fields keep admin defaults and stay optional.

    ``field_annotations`` supplies the plain value type per field (from
    :func:`field_plan`); ``field_defaults`` supplies the admin default value.
    """
    if not exposed_fields:
        raise ValueError("exposed_fields must contain at least one field name")

    field_definitions: dict[str, tuple[Any, Any]] = {}
    for exposed_name in exposed_fields:
        field_name = resolve_field_name(call_schema, exposed_name)
        field_info = call_schema.model_fields[field_name]
        has_default_override = (
            field_defaults is not None and field_name in field_defaults
        )
        resolved_annotation = (
            field_annotations.get(field_name)
            if field_annotations is not None
            else None
        )
        field_definitions[field_name] = field_definition_from_info(
            field_info,
            annotation=resolved_annotation,
            default_override=(
                field_defaults.get(field_name) if has_default_override else None
            ),
            use_default_override=has_default_override,
        )
    return _project(call_schema, field_definitions)


class ConfigRequestResolver:
    """Single owner of config -> request/call-schema/value resolution."""

    @staticmethod
    @lru_cache(maxsize=64)
    def request_model(config_cls: type[ConfigT]) -> type[BaseModel]:
        """Derive ``POST /v1/search`` body: ``query`` + config fields as plain types."""
        return _build_model(
            config_cls,
            name=_search_request_model_name(config_cls, agent=False),
            base=SearchRequestBase,
            unwrap=True,
            exclude=frozenset(),
        )

    @staticmethod
    @lru_cache(maxsize=64)
    def agent_request_model(config_cls: type[ConfigT]) -> type[BaseModel]:
        """Derive ``POST /v1/agent-search`` body: ``query`` + config fields."""
        return _build_model(
            config_cls,
            name=_search_request_model_name(config_cls, agent=True),
            base=AgentRequestBase,
            unwrap=False,
            exclude=_AGENT_EXCLUDED,
        )

    @staticmethod
    @lru_cache(maxsize=64)
    def crawl_request_model(config_cls: type[ConfigT]) -> type[BaseModel]:
        """Derive ``POST /v1/crawl`` body: ``urls`` + all config fields."""
        return _build_model(
            config_cls,
            name=f"{config_cls.__name__.removesuffix('Config')}CrawlRequest",
            base=CrawlRequestBase,
            unwrap=False,
            exclude=frozenset(),
        )

    @staticmethod
    def exposed_field_names(config: BaseModel, *, with_query: bool = True) -> list[str]:
        """Field names exposed to LLM callers (optionally including ``query``)."""
        names = [QUERY_FIELD] if with_query else []
        for name, info in type(config).model_fields.items():
            if not is_exposable_param_field(info):
                continue
            raw = getattr(config, name)
            if isinstance(raw, ExposableParam) and raw.expose:
                names.append(name)
        return names

    @staticmethod
    def resolve_values(
        config: BaseModel,
        *,
        exclude: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        """Plain deployment defaults (ExposableParam broken down; deactivated dropped)."""
        out: dict[str, Any] = {}
        for name, info in type(config).model_fields.items():
            if name in exclude:
                continue
            raw = getattr(config, name)
            if is_exposable_param_field(info):
                value = raw.value if isinstance(raw, ExposableParam) else raw
                if value is not None:
                    out[name] = value
            elif raw is not None:
                out[name] = raw
        return out

    @staticmethod
    def call_schema(config: BaseModel, *, strict: bool = True) -> type[BaseModel]:
        """LLM call-schema model from a config instance (query + ``expose=True`` fields)."""
        request_model = ConfigRequestResolver.request_model(type(config))
        exposed = ConfigRequestResolver.exposed_field_names(config, with_query=True)
        if strict:
            return project_strict(request_model, exposed)
        return project_non_strict(
            request_model,
            exposed,
            field_defaults=ConfigRequestResolver.resolve_values(config),
            field_annotations={
                plan.name: plan.inner_type for plan in field_plan(type(config))
            },
        )


__all__ = [
    "ConfigRequestResolver",
]
