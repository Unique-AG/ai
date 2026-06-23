from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from unique_search_proxy_client.web.app import create_app


@pytest.fixture
def client() -> TestClient:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def bing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BING_AGENT_ENDPOINT", "https://example.azure.com")
    monkeypatch.setenv(
        "BING_AGENT_BING_RESOURCE_CONNECTION_STRING",
        "/subscriptions/test/resourceGroups/r/providers/...",
    )
    monkeypatch.setenv("BING_AGENT_AGENT_ID", "agent-123")


def _agent_search_body(**fields: Any) -> dict[str, Any]:
    return {
        "engine": "bing",
        "query": "test query",
        "fetchSize": 5,
        "timeout": 120,
        **fields,
    }


class TestAgentSearchRoute:
    @pytest.mark.ai
    def test_agent_search_returns_answer(
        self, client: TestClient, bing_env: None
    ) -> None:
        with patch(
            "unique_search_proxy_client.web.api.v1.agent_search.get_agent_engine_service",
        ) as get_service:
            mock_engine = AsyncMock()
            mock_engine.search = AsyncMock(
                return_value=type(
                    "R",
                    (),
                    {
                        "engine": "bing",
                        "query": "test query",
                        "answer": "done",
                        "raw": {},
                    },
                )(),
            )
            from unique_search_proxy_core.schema import AgentSearchResponse

            mock_engine.search = AsyncMock(
                return_value=AgentSearchResponse(
                    engine="bing",
                    query="test query",
                    answer="done",
                    raw={},
                ),
            )
            get_service.return_value = mock_engine

            resp = client.post("/v1/agent-search", json=_agent_search_body())

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "done"
        assert body["engine"] == "bing"

    @pytest.mark.ai
    def test_list_providers_includes_agent_engines(self, client: TestClient) -> None:
        resp = client.get("/v1/configuration/providers")
        assert resp.status_code == 200
        body = resp.json()
        assert "bing" in body["agentEngines"]
        assert "vertexai" in body["agentEngines"]
