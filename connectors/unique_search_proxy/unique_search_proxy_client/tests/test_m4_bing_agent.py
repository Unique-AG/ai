from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.core.agent_engines.bing.service import (
    BingAgentSearchService,
)


def _bing_request(**fields: Any) -> BingAgentSearchRequest:
    return BingAgentSearchRequest.model_validate(
        {
            "query": "hello",
            "fetch_size": 5,
            "timeout": 120,
            **fields,
        },
    )


@pytest.fixture
def bing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BING_AGENT_ENDPOINT", "https://example.azure.com")
    monkeypatch.setenv(
        "BING_AGENT_BING_RESOURCE_CONNECTION_STRING",
        "/subscriptions/test/resourceGroups/r/providers/...",
    )
    monkeypatch.setenv("BING_AGENT_AGENT_ID", "agent-123")
    monkeypatch.setenv("BING_AGENT_BING_AGENT_MODEL", "gpt-4o-deployment")
    from unique_search_proxy_client.web.settings.providers import bing_agent

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.agent_engines.bing.service.bing_agent_credentials",
        bing_agent._get_bing_agent_credentials(),
    )


class TestBingAgentSearchService:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_search_returns_answer_and_raw(self, bing_env: None) -> None:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.service.get_credentials",
                return_value=MagicMock(),
            ),
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.service.get_project_client",
                return_value=mock_client,
            ),
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.service.run_bing_grounding_agent",
                new_callable=AsyncMock,
                return_value=("agent answer text", {"messages": []}),
            ),
        ):
            service = BingAgentSearchService()
            result = await service.search(_bing_request())

        assert result.answer == "agent answer text"
        assert result.engine == "bing"
        assert result.raw == {"messages": []}

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_missing_credentials_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BING_AGENT_ENDPOINT", raising=False)
        from unique_search_proxy_client.web.settings.providers import bing_agent

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.agent_engines.bing.service.bing_agent_credentials",
            bing_agent._get_bing_agent_credentials(),
        )
        service = BingAgentSearchService()
        with pytest.raises(EngineNotConfiguredError):
            await service.search(_bing_request())
