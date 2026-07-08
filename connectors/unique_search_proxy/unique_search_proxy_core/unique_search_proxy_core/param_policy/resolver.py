"""Single orchestrator for config -> request/call-schema/value resolution.

``ConfigRequestResolver`` folds the previously scattered derivation helpers
(``derive_request_model``, ``build_request_model``, ``build_agent_request_model``,
``build_llm_call_model``, ``merge_config_and_invocation``, ``config_defaults``,
``llm_exposed_field_names``, ``provider_query_params_from_request``) into one place.
The required ``query`` field comes from ``SearchRequestBase`` / ``AgentRequestBase``
instead of an inline ``leading_fields`` tuple.
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, TypeVar, cast

from pydantic import BaseModel, create_model

from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.param_policy.annotations import (
    field_definition_from_info,
    plain_annotation_for_llm,
    plain_annotation_for_non_strict_llm,
    plain_annotation_for_request,
    resolve_field_name,
)
from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    is_exposable_param_field,
    is_exposable_param_type,
)
from unique_search_proxy_core.param_policy.request_base import (
    AgentRequestBase,
    CrawlRequestBase,
    SearchRequestBase,
)
from unique_search_proxy_core.schema import camelized_model_config

ENGINE_FIELD = "engine"
_MERGE_ALWAYS_INCLUDE = frozenset({"fetch_size", "timeout", "safe"})
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
    for field_name, info in config_cls.model_fields.items():
        if field_name in exclude:
            continue
        fields[field_name] = field_definition_from_info(
            info,
            annotation=plain_annotation_for_request(info.annotation),
            force_default_none=unwrap and is_exposable_param_type(info.annotation),
        )
    model = create_model(
        name,
        __base__=base,
        **cast(Any, fields),
    )
    config_module = importlib.import_module(config_cls.__module__)
    model.model_rebuild(_types_namespace=dict(vars(config_module)))
    return model


def project_call_schema(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
    *,
    model_name_suffix: str = "LlmProjection",
    strict_required: bool = False,
    field_defaults: dict[str, Any] | None = None,
    config_field_annotations: dict[str, Any] | None = None,
) -> type[BaseModel]:
    """Project a call schema down to the fields exposed to LLM-driven callers."""
    if not exposed_fields:
        raise ValueError("exposed_fields must contain at least one field name")

    field_definitions: dict[str, tuple[Any, Any]] = {}
    for exposed_name in exposed_fields:
        field_name = resolve_field_name(call_schema, exposed_name)
        field_info = call_schema.model_fields[field_name]
        default_override = (
            field_defaults.get(field_name) if field_defaults is not None else None
        )
        has_default_override = (
            field_defaults is not None and field_name in field_defaults
        )
        config_ann = (
            config_field_annotations.get(field_name)
            if config_field_annotations is not None
            else None
        )
        if strict_required:
            resolved_annotation = plain_annotation_for_llm(field_info.annotation)
        elif config_ann is not None:
            resolved_annotation = plain_annotation_for_non_strict_llm(config_ann)
        else:
            resolved_annotation = None
        field_definitions[field_name] = field_definition_from_info(
            field_info,
            annotation=resolved_annotation,
            strict_required=strict_required,
            default_override=default_override if has_default_override else None,
            use_default_override=has_default_override,
        )

    model_config = call_schema.model_config or camelized_model_config
    return create_model(
        f"{call_schema.__name__}{model_name_suffix}",
        __config__=model_config,
        **cast(Any, field_definitions),
    )


def project_json_schema(
    call_schema: type[BaseModel],
    exposed_fields: list[str],
) -> dict[str, Any]:
    """Return the JSON schema for the LLM-facing projection of a call schema."""
    projected = project_call_schema(call_schema, exposed_fields)
    return projected.model_json_schema()


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
                value = raw.resolve() if isinstance(raw, ExposableParam) else raw
                if value is not None:
                    out[name] = value
            elif raw is not None or name in _MERGE_ALWAYS_INCLUDE:
                out[name] = raw
        return out

    @staticmethod
    def merge(
        config: BaseModel,
        overrides: dict[str, Any],
        *,
        query: str,
    ) -> BaseModel:
        """Merge deployment defaults + caller/LLM overrides + query into a request model."""
        request_model = ConfigRequestResolver.request_model(type(config))
        merged: dict[str, Any] = {
            **ConfigRequestResolver.resolve_values(
                config, exclude=frozenset({ENGINE_FIELD})
            ),
            **overrides,
            QUERY_FIELD: query,
        }
        engine = getattr(config, ENGINE_FIELD, None)
        if engine is not None and ENGINE_FIELD in request_model.model_fields:
            merged[ENGINE_FIELD] = getattr(engine, "value", engine)
        return request_model.model_validate(merged)

    @staticmethod
    def provider_query_params(
        request: BaseModel,
        config_cls: type[BaseModel],
        *,
        by_alias: bool = True,
    ) -> dict[str, Any]:
        """Serialize provider knobs from a merged request model.

        Fields the config marks as non-forwardable (via
        ``provider_param_exclude_fields``) are dropped so credentials and
        request plumbing never leak into the upstream query string.
        """
        from unique_search_proxy_core.search_engines.base import (
            BaseSearchEngineConfig,
        )

        exclude: set[str] = set()
        if issubclass(config_cls, BaseSearchEngineConfig):
            exclude = config_cls.provider_param_exclude_fields()

        return request.model_dump(
            mode="json",
            exclude_none=True,
            by_alias=by_alias,
            exclude=exclude,
        )

    @staticmethod
    def call_schema(config: BaseModel, *, strict: bool = True) -> type[BaseModel]:
        """LLM call-schema model from a config instance (query + ``expose=True`` fields)."""
        request_model = ConfigRequestResolver.request_model(type(config))
        exposed = ConfigRequestResolver.exposed_field_names(config, with_query=True)
        defaults = None if strict else ConfigRequestResolver.resolve_values(config)
        config_ann = {
            name: info.annotation for name, info in type(config).model_fields.items()
        }
        return project_call_schema(
            request_model,
            exposed,
            strict_required=strict,
            field_defaults=defaults,
            config_field_annotations=config_ann,
        )


__all__ = [
    "ConfigRequestResolver",
    "project_call_schema",
    "project_json_schema",
]
