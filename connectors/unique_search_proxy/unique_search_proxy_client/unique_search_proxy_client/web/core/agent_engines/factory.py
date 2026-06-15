from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from unique_search_proxy_core.agent_engines.base import (
    AgentEngineType,
    AgentSearchEngine,
)

from unique_search_proxy_client.web.core.agent_engines.bing.service import (
    BingAgentSearchService,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.service import (
    VertexAIAgentSearchService,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


def get_agent_engine_service(
    engine: AgentEngineType,
    *,
    http_client: AsyncClient | None = None,
) -> AgentSearchEngine[Any]:
    """Instantiate an agent search engine by registered id."""
    match engine:
        case AgentEngineType.BING:
            return BingAgentSearchService(http_client=http_client)
        case AgentEngineType.VERTEXAI:
            return VertexAIAgentSearchService(http_client=http_client)
        case _:
            msg = f"Unsupported agent engine: {engine}"
            raise ValueError(msg)


def get_request_model_for_agent_engine(engine_id: str) -> type[BaseModel]:
    from unique_search_proxy_client.web.core.registry import (
        get_agent_engine_descriptor,
    )

    descriptor = get_agent_engine_descriptor(engine_id)
    if descriptor is None:
        msg = f"No descriptor for agent engine: {engine_id}"
        raise ValueError(msg)
    return descriptor.request_model


class AgentEngineDescriptor:
    def __init__(
        self,
        *,
        config_model: type[BaseModel],
        service_cls: type[AgentSearchEngine[Any]],
        request_model: type[BaseModel],
    ) -> None:
        self.config_model = config_model
        self.service_cls = service_cls
        self.request_model = request_model


__all__ = [
    "AgentEngineDescriptor",
    "get_agent_engine_service",
    "get_request_model_for_agent_engine",
]
