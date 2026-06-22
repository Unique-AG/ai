from unique_search_proxy_core.agent_engines.base import AgentEngineType
from unique_search_proxy_core.agent_engines.bing.schema import (
    BingAgentConfig,
    BingAgentSearchRequest,
)
from unique_search_proxy_core.agent_engines.vertexai.schema import (
    VertexAIAgentConfig,
    VertexAIAgentSearchRequest,
)

from unique_search_proxy_client.web.core.agent_engines.bing.service import (
    BingAgentSearchService,
)
from unique_search_proxy_client.web.core.agent_engines.factory import (
    AgentEngineDescriptor,
    get_agent_engine_service,
)
from unique_search_proxy_client.web.core.agent_engines.vertexai.service import (
    VertexAIAgentSearchService,
)


def register_builtin_agent_engines() -> None:
    from unique_search_proxy_client.web.core.registry import register_agent_engine

    register_agent_engine(
        AgentEngineType.BING.value,
        BingAgentSearchService,
        descriptor=AgentEngineDescriptor(
            config_model=BingAgentConfig,
            service_cls=BingAgentSearchService,
            request_model=BingAgentSearchRequest,
        ),
    )
    register_agent_engine(
        AgentEngineType.VERTEXAI.value,
        VertexAIAgentSearchService,
        descriptor=AgentEngineDescriptor(
            config_model=VertexAIAgentConfig,
            service_cls=VertexAIAgentSearchService,
            request_model=VertexAIAgentSearchRequest,
        ),
    )


__all__ = [
    "AgentEngineDescriptor",
    "BingAgentConfig",
    "BingAgentSearchService",
    "VertexAIAgentConfig",
    "VertexAIAgentSearchService",
    "get_agent_engine_service",
    "register_builtin_agent_engines",
]
