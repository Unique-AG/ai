"""Model factories: deployment config class -> derived Pydantic models.

Private-by-convention; the public entry points are the config-class methods
(``BaseSearchEngineConfig.request_model()`` / ``exposed_params_model()`` and the
agent/crawler ``request_model()`` counterparts), which delegate here.

Two factories, both plain ``create_model`` calls over ``model_fields``:

- :func:`derive_request_model` — HTTP request body: a request base class
  (required ``query`` / ``urls``) + the config's fields, with ``ExposableParam``
  knobs unwrapped to optional plain types (default ``None``; admin defaults are
  merged at search time, never baked into the request schema).
- :func:`derive_exposed_params_model` — LLM-facing :class:`ExposedParams`
  subclass with exactly the knobs the deployment marked ``expose=True``.
"""

from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, Field, create_model
from pydantic.alias_generators import to_camel

from unique_search_proxy_core.param_policy.annotations import (
    FieldDefinition,
    as_optional,
    plain_inner_type,
    request_field_definition,
)
from unique_search_proxy_core.param_policy.exposable_param import (
    ExposableParam,
    is_exposable_param_field,
)
from unique_search_proxy_core.param_policy.exposed_params import ExposedParams


@lru_cache(maxsize=64)
def derive_request_model(
    config_cls: type[BaseModel],
    *,
    base: type[BaseModel],
    name: str,
    exclude: frozenset[str] = frozenset(),
) -> type[BaseModel]:
    """Derive an HTTP request model from a config class (cached per signature).

    ``base`` supplies the required leading field (``SearchRequestBase.query`` /
    ``CrawlRequestBase.urls``) and the model config. Config fields keep their
    metadata and defaults; ``ExposableParam`` knobs become optional plain types
    with a ``None`` default.

    Example: ``derive_request_model(GoogleConfig, base=SearchRequestBase,
    name="GoogleSearchRequest")``.
    """
    field_definitions: dict[str, FieldDefinition] = {}
    for field_name, field_info in config_cls.model_fields.items():
        if field_name in exclude:
            continue
        exposable = is_exposable_param_field(field_info)
        annotation = plain_inner_type(field_info.annotation)
        if exposable:
            annotation = as_optional(annotation)
        field_definitions[field_name] = request_field_definition(
            field_info,
            annotation=annotation,
            default_none=exposable,
        )

    model = create_model(
        name,
        __base__=base,
        **cast(Any, field_definitions),
    )
    # Schema modules use `from __future__ import annotations`; resolve any
    # stringified forward references against the config module's namespace.
    config_module = importlib.import_module(config_cls.__module__)
    model.model_rebuild(_types_namespace=dict(vars(config_module)))
    return model


def derive_exposed_params_model(
    config: BaseModel,
    *,
    name: str,
) -> type[ExposedParams] | None:
    """Derive the LLM-facing exposed-params model from a config instance.

    One optional field per ``ExposableParam`` knob with ``expose=True``: plain
    inner type ``| None``, default ``None``, camelCase alias, description copied
    from the config field. Admin default values never appear. Returns ``None``
    when the deployment exposes nothing.

    Example: ``derive_exposed_params_model(config, name="GoogleExposedParams")``.
    """
    field_definitions: dict[str, FieldDefinition] = {}
    for field_name, field_info in type(config).model_fields.items():
        if not is_exposable_param_field(field_info):
            continue
        param = getattr(config, field_name)
        if not isinstance(param, ExposableParam) or not param.expose:
            continue
        field_definitions[field_name] = (
            as_optional(plain_inner_type(field_info.annotation)),
            Field(
                default=None,
                description=field_info.description or field_name,
                alias=field_info.alias or to_camel(field_name),
            ),
        )

    if not field_definitions:
        return None
    return create_model(
        name,
        __base__=ExposedParams,
        **cast(Any, field_definitions),
    )
