from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, cast

from pydantic import BaseModel, Field, create_model

from unique_search_proxy_core.param_policy import QUERY_FIELD
from unique_search_proxy_core.projection import (
    _field_definition_from_info,
    _plain_annotation_for_request,
)
from unique_search_proxy_core.schema import camelized_model_config

_AGENT_REQUEST_EXCLUDED_FIELDS = frozenset({"output_schema"})


def _agent_request_model_name(config_cls: type[BaseModel]) -> str:
    """``BingAgentConfig`` -> ``BingAgentSearchRequest``."""
    base = config_cls.__name__
    if base.endswith("Config"):
        base = base[: -len("Config")]
    if base.endswith("Agent"):
        return f"{base}SearchRequest"
    return f"{base}AgentSearchRequest"


@lru_cache(maxsize=32)
def build_agent_request_model(config_cls: type[BaseModel]) -> type[BaseModel]:
    """Derive ``POST /v1/agent-search`` body: ``query`` + all config fields."""
    field_definitions: dict[str, tuple[Any, Any]] = {
        QUERY_FIELD: (
            str,
            Field(
                ...,
                min_length=1,
                description="Search query string",
            ),
        ),
    }
    for field_name, field_info in config_cls.model_fields.items():
        if field_name in _AGENT_REQUEST_EXCLUDED_FIELDS:
            continue
        plain_annotation = _plain_annotation_for_request(field_info.annotation)
        field_definitions[field_name] = _field_definition_from_info(
            field_info,
            annotation=plain_annotation,
            force_default_none=False,
        )

    model_config = config_cls.model_config or camelized_model_config
    request_model = create_model(
        _agent_request_model_name(config_cls),
        __config__=model_config,
        **cast(Any, field_definitions),
    )
    config_module = importlib.import_module(config_cls.__module__)
    request_model.model_rebuild(_types_namespace=dict(vars(config_module)))
    return request_model


__all__ = ["build_agent_request_model"]
