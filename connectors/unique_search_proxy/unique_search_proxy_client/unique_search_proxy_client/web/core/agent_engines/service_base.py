from __future__ import annotations

from typing import TYPE_CHECKING, Generic

from unique_search_proxy_core.agent_engines.base import (
    AgentRequestT,
    AgentSearchEngine,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from unique_search_proxy_core.http_client import EgressRoute


class AgentSearchEngineService(
    AgentSearchEngine[AgentRequestT], Generic[AgentRequestT]
):
    """Client-side agent search engine base (HTTP client wiring)."""

    def __init__(
        self,
        *,
        http_client: AsyncClient | None = None,
        egress_route: EgressRoute | None = None,
    ) -> None:
        super().__init__(http_client=http_client)
        self._egress_route = egress_route

    @property
    def mode(self) -> str:
        return "agent"
