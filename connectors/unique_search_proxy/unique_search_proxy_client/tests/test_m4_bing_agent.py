from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import NotFoundError
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.core.agent_engines.bing.runner import (
    _agent_name_for_config,
    _config_hash,
    _is_missing_agent_error,
    create_bing_agent,
    get_bing_grounding_tool,
    resolve_bing_agent_name,
    stream_bing_grounding_agent,
)
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


async def _fake_stream(
    *_args: Any,
    **_kwargs: Any,
) -> AsyncIterator[tuple[str, Any]]:
    yield "agent answer text", {"messages": []}


async def _fake_response_events() -> AsyncIterator[Any]:
    event = MagicMock()
    event.type = "response.output_text.delta"
    event.delta = "agent answer text"
    event.model_dump_json = MagicMock(return_value='{"type":"response.output_text.delta"}')
    yield event
    done = MagicMock()
    done.type = "response.completed"
    done.response = MagicMock()
    done.response.output_text = "agent answer text"
    done.response.model_dump_json = MagicMock(
        return_value='{"output_text":"agent answer text"}'
    )
    done.model_dump_json = MagicMock(return_value='{"type":"response.completed"}')
    yield done


@pytest.fixture
def bing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BING_AGENT_ENDPOINT", "https://example.azure.com")
    monkeypatch.setenv(
        "BING_AGENT_BING_RESOURCE_CONNECTION_STRING",
        "/subscriptions/test/resourceGroups/r/providers/.../connections/TestBing",
    )
    monkeypatch.setenv("BING_AGENT_AGENT_ID", "agent-123")
    monkeypatch.setenv("BING_AGENT_BING_AGENT_MODEL", "gpt-5.1")
    from unique_search_proxy_client.web.settings.providers import bing_agent

    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.agent_engines.bing.service.bing_agent_credentials",
        bing_agent._get_bing_agent_credentials(),
    )
    monkeypatch.setattr(
        "unique_search_proxy_client.web.core.agent_engines.bing.runner.settings.bing_agent_credentials",
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
                "unique_search_proxy_client.web.core.agent_engines.bing.service.stream_bing_grounding_agent",
                side_effect=_fake_stream,
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


class TestGetBingGroundingTool:
    @pytest.mark.ai
    def test_builds_nested_search_configuration(self, bing_env: None) -> None:
        tool = get_bing_grounding_tool(fetch_size=7)
        configs = tool.bing_grounding.search_configurations
        assert len(configs) == 1
        assert (
            configs[0].project_connection_id
            == "/subscriptions/test/resourceGroups/r/providers/.../connections/TestBing"
        )
        assert configs[0].count == 7


class TestConfigHashAndAgentName:
    @pytest.mark.ai
    def test_same_inputs_produce_same_hash_and_name(self) -> None:
        a = _config_hash(model="gpt-5.1", fetch_size=5, instructions="Be helpful.")
        b = _config_hash(model="gpt-5.1", fetch_size=5, instructions="Be helpful.")
        assert a == b
        assert len(a) == 12
        assert (
            _agent_name_for_config(
                model="gpt-5.1", fetch_size=5, instructions="Be helpful."
            )
            == f"unique-grounding-with-bing-{a}"
        )

    @pytest.mark.ai
    def test_different_fetch_size_or_instructions_change_name(self) -> None:
        base = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions="Be helpful."
        )
        other_size = _agent_name_for_config(
            model="gpt-5.1", fetch_size=10, instructions="Be helpful."
        )
        other_instructions = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions="Be concise."
        )
        assert base != other_size
        assert base != other_instructions
        assert other_size != other_instructions

    @pytest.mark.ai
    def test_different_model_changes_name(self) -> None:
        base = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions="Be helpful."
        )
        other_model = _agent_name_for_config(
            model="gpt-4o", fetch_size=5, instructions="Be helpful."
        )
        assert base != other_model

    @pytest.mark.ai
    def test_resolve_prefers_preconfigured_name(self) -> None:
        assert (
            resolve_bing_agent_name(
                model="gpt-5.1",
                fetch_size=5,
                instructions="Be helpful.",
                agent_name="my-agent",
            )
            == "my-agent"
        )


class TestMissingAgentError:
    @pytest.mark.ai
    def test_detects_openai_not_found(self) -> None:
        exc = NotFoundError(
            message="Agent unique-grounding-with-bing-abc not found",
            response=MagicMock(status_code=404, headers={}),
            body=None,
        )
        assert _is_missing_agent_error(exc, agent_name="unique-grounding-with-bing-abc")


class TestCreateAndStreamOptimistic:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_create_bing_agent_calls_create_version(self, bing_env: None) -> None:
        expected_name = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions="Be helpful."
        )
        created = MagicMock()
        created.name = expected_name
        created.id = "new-agent-id"
        mock_client = MagicMock()
        mock_client.agents.create_version = AsyncMock(return_value=created)

        name = await create_bing_agent(
            mock_client,
            agent_name=expected_name,
            model="gpt-5.1",
            fetch_size=5,
            instructions="Be helpful.",
        )

        assert name == expected_name
        call_kwargs = mock_client.agents.create_version.await_args.kwargs
        assert call_kwargs["agent_name"] == expected_name
        assert call_kwargs["definition"].instructions == "Be helpful."

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_stream_creates_agent_when_responses_reports_missing(
        self, bing_env: None
    ) -> None:
        expected_name = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions="Be helpful."
        )
        missing = NotFoundError(
            message=f"Agent {expected_name} not found",
            response=MagicMock(status_code=404, headers={}),
            body=None,
        )
        mock_openai = MagicMock()
        mock_openai.responses.create = AsyncMock(
            side_effect=[missing, _fake_response_events()],
        )
        created = MagicMock()
        created.name = expected_name
        created.id = "created-id"
        mock_client = MagicMock()
        mock_client.agents.create_version = AsyncMock(return_value=created)

        with patch(
            "unique_search_proxy_client.web.core.agent_engines.bing.runner.get_openai_client",
            return_value=mock_openai,
        ):
            chunks = [
                item
                async for item in stream_bing_grounding_agent(
                    mock_client,
                    query="hello",
                    model="gpt-5.1",
                    fetch_size=5,
                    instructions="Be helpful.",
                )
            ]

        assert chunks[0][0] == "agent answer text"
        mock_client.agents.create_version.assert_awaited_once()
        assert mock_openai.responses.create.await_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_stream_does_not_create_for_preconfigured_agent(
        self, bing_env: None
    ) -> None:
        missing = NotFoundError(
            message="Agent my-preconfigured-agent not found",
            response=MagicMock(status_code=404, headers={}),
            body=None,
        )
        mock_openai = MagicMock()
        mock_openai.responses.create = AsyncMock(side_effect=missing)
        mock_client = MagicMock()

        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.runner.get_openai_client",
                return_value=mock_openai,
            ),
            pytest.raises(NotFoundError),
        ):
            async for _ in stream_bing_grounding_agent(
                mock_client,
                query="hello",
                model="gpt-5.1",
                fetch_size=5,
                instructions="Be helpful.",
                agent_name="my-preconfigured-agent",
            ):
                pass

        mock_client.agents.create_version.assert_not_called()
