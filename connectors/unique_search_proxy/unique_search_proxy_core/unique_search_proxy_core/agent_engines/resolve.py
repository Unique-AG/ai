from __future__ import annotations

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    BaseAgentEngineConfig,
)
from unique_search_proxy_core.agent_engines.config_types import ENGINE_NAME_TO_CONFIG


def resolve_output_schema(
    config_cls: type[BaseAgentEngineConfig],
) -> type[BaseModel]:
    """Return the configured structured-output model for an agent engine."""
    field_info = config_cls.model_fields["output_schema"]
    default = field_info.default
    if default is not PydanticUndefined and isinstance(default, type):
        return default
    msg = f"{config_cls.__name__} is missing a default output_schema"
    raise ValueError(msg)


def resolve_output_schema_for_engine(engine: AgentEngineType | str) -> type[BaseModel]:
    """Resolve structured-output model from a registered engine id."""
    engine_id = engine.value if isinstance(engine, AgentEngineType) else engine
    config_cls = ENGINE_NAME_TO_CONFIG.get(engine_id.lower())
    if config_cls is None:
        msg = f"No agent engine config registered for {engine_id!r}"
        raise ValueError(msg)
    return resolve_output_schema(config_cls)


__all__ = ["resolve_output_schema", "resolve_output_schema_for_engine"]
