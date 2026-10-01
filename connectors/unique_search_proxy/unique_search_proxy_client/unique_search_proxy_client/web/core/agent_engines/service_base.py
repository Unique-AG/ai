from __future__ import annotations

from typing import TYPE_CHECKING, Generic

from unique_search_proxy_core.agent_engines.base import (
    AgentRequestT,
    AgentSearchEngine,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


class AgentSearchEngineService(
    AgentSearchEngine[AgentRequestT], Generic[AgentRequestT]
):
    """Client-side agent search engine base (HTTP client wiring)."""

    def __init__(
        self,
        *,
        http_client: AsyncClient | None = None,
        egress_requires_proxy: bool = False,
    ) -> None:
        super().__init__(http_client=http_client)
        self._egress_requires_proxy = egress_requires_proxy

    @property
    def mode(self) -> str:
        return "agent"
