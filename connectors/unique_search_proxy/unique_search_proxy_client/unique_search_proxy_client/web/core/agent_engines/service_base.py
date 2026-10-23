from __future__ import annotations

from typing import Generic

from unique_search_proxy_core.agent_engines.base import (
    AgentRequestT,
    AgentSearchEngine,
)


class AgentSearchEngineService(
    AgentSearchEngine[AgentRequestT], Generic[AgentRequestT]
):
    """Client-side agent search engine base (HTTP client wiring)."""

    @property
    def mode(self) -> str:
        return "agent"
