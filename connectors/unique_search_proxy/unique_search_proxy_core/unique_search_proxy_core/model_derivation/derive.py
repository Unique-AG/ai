from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel, create_model

from unique_search_proxy_core.model_derivation.fields import (
    field_definition_from_info,
    plain_annotation_for_request,
)
from unique_search_proxy_core.param_policy.exposable_param import (
    is_exposable_param_type,
)
from unique_search_proxy_core.schema import camelized_model_config


def derive_request_model(
    config_cls: type[BaseModel],
    *,
    leading_fields: tuple[tuple[str, tuple[Any, Any]], ...],
    model_name: Callable[[type[BaseModel]], str],
    exclude_fields: frozenset[str] = frozenset(),
    unwrap_exposable_params: bool = False,
) -> type[BaseModel]:
    """Derive an HTTP request model from a deployment config class."""
    field_definitions: dict[str, tuple[Any, Any]] = dict(leading_fields)
    for field_name, field_info in config_cls.model_fields.items():
        if field_name in exclude_fields:
            continue
        plain_annotation = plain_annotation_for_request(field_info.annotation)
        force_default_none = (
            is_exposable_param_type(field_info.annotation)
            if unwrap_exposable_params
            else False
        )
        field_definitions[field_name] = field_definition_from_info(
            field_info,
            annotation=plain_annotation,
            force_default_none=force_default_none,
        )

    model_config = config_cls.model_config or camelized_model_config
    request_model = create_model(
        model_name(config_cls),
        __config__=model_config,
        **cast(Any, field_definitions),
    )
    config_module = importlib.import_module(config_cls.__module__)
    request_model.model_rebuild(_types_namespace=dict(vars(config_module)))
    return request_model
