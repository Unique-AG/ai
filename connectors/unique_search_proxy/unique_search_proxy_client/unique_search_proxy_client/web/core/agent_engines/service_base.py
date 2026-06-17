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
    ) -> None:
        super().__init__(http_client=http_client)

    @property
    def mode(self) -> str:
        return "agent"
