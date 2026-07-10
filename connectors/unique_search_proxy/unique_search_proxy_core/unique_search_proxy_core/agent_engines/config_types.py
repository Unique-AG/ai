from __future__ import annotations

import operator
from functools import reduce
from typing import Annotated, Any, Mapping, TypeAlias, Union, cast

from pydantic import BaseModel, Field, TypeAdapter

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentConfig
from unique_search_proxy_core.agent_engines.vertexai.schema import VertexAIAgentConfig

AgentEngineConfigTypes: TypeAlias = BingAgentConfig | VertexAIAgentConfig

ENGINE_NAME_TO_CONFIG: dict[str, type[BaseAgentEngineConfig]] = {
    AgentEngineType.BING.value: BingAgentConfig,
    AgentEngineType.VERTEXAI.value: VertexAIAgentConfig,
}

_agent_engine_config_adapter: TypeAdapter[AgentEngineConfigTypes] = TypeAdapter(
    AgentEngineConfigTypes,
)


def parse_agent_engine_config(data: object) -> AgentEngineConfigTypes:
    return _agent_engine_config_adapter.validate_python(data)


def get_agent_engine_config_types_from_names(
    engine_names: list[str],
) -> type[BaseAgentEngineConfig]:
    assert len(engine_names) >= 1, "At least one agent engine must be active"

    selected_types = [
        ENGINE_NAME_TO_CONFIG[name.lower()]
        for name in engine_names
        if name.lower() in ENGINE_NAME_TO_CONFIG
    ]
    if not selected_types:
        raise ValueError(f"No agent engine config found for names: {engine_names}")
    if len(selected_types) == 1:
        return selected_types[0]
    return cast(type[BaseAgentEngineConfig], reduce(operator.or_, selected_types))


def _union_members_from_mapping(
    mapping: Mapping[str, type[BaseAgentEngineConfig]],
) -> tuple[type[BaseAgentEngineConfig], ...]:
    return tuple(mapping.values())


def build_agent_search_request_union() -> Any:
    """Discriminated union of flat ``POST /v1/agent-search`` bodies."""
    members = _union_members_from_mapping(ENGINE_NAME_TO_CONFIG)
    request_models = tuple(config_cls.request_model() for config_cls in members)
    if len(request_models) == 1:
        return request_models[0]
    return Annotated[
        Union[request_models],  # type: ignore[valid-type]
        Field(discriminator="engine"),
    ]


AgentSearchRequestTypes = build_agent_search_request_union()
AgentSearchRequest = AgentSearchRequestTypes

_agent_search_request_adapter: TypeAdapter[BaseModel] = TypeAdapter(
    AgentSearchRequestTypes,  # type: ignore[arg-type]
)


def parse_agent_search_request(data: object) -> BaseModel:
    return _agent_search_request_adapter.validate_python(data)


__all__ = [
    "AgentEngineConfigTypes",
    "AgentSearchRequest",
    "AgentSearchRequestTypes",
    "ENGINE_NAME_TO_CONFIG",
    "build_agent_search_request_union",
    "get_agent_engine_config_types_from_names",
    "parse_agent_engine_config",
    "parse_agent_search_request",
]
