from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import NotFoundError
from openai.types.responses.response import Response
from openai.types.responses.response_completed_event import ResponseCompletedEvent
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from unique_search_proxy_core.agent_engines.bing.schema import BingAgentSearchRequest
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.core.agent_engines.bing.cleanup import (
    cleanup_auto_provisioned_bing_agents,
    maybe_cleanup_auto_provisioned_bing_agents_on_start,
)
from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    aclose_private_endpoint_http_client,
)
from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    get_openai_client as get_openai_client_from_client_module,
)
from unique_search_proxy_client.web.core.agent_engines.bing.runner import (
    BING_AUTO_AGENT_NAME_PREFIX,
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


class _CloseableAsyncStream:
    """Stand-in for ``openai.AsyncStream`` (async iteration + context manager)."""

    def __init__(self, agen: AsyncIterator[Any]) -> None:
        self._agen = agen
        self.closed = False

    async def __aenter__(self) -> _CloseableAsyncStream:
        return self

    async def __aexit__(self, *_args: object) -> None:
        self.closed = True
        aclose = getattr(self._agen, "aclose", None)
        if aclose is not None:
            await aclose()

    def __aiter__(self) -> AsyncIterator[Any]:
        return self._agen


async def _fake_response_events(*, with_deltas: bool = True) -> AsyncIterator[Any]:
    if with_deltas:
        yield ResponseTextDeltaEvent.model_construct(
            type="response.output_text.delta",
            delta="agent answer text",
            content_index=0,
            item_id="item-1",
            output_index=0,
            sequence_number=1,
            logprobs=[],
        )
    text = ResponseOutputText.model_construct(
        type="output_text",
        text="agent answer text",
        annotations=[],
        logprobs=[],
    )
    message = ResponseOutputMessage.model_construct(
        type="message",
        id="msg-1",
        role="assistant",
        status="completed",
        content=[text],
    )
    response = Response.model_construct(
        id="resp-1",
        created_at=0,
        model="gpt-5.1",
        object="response",
        output=[message],
        parallel_tool_calls=True,
        tool_choice="auto",
        tools=[],
    )
    yield ResponseCompletedEvent.model_construct(
        type="response.completed",
        sequence_number=2,
        response=response,
    )


def _fake_response_stream(*, with_deltas: bool = True) -> _CloseableAsyncStream:
    return _CloseableAsyncStream(_fake_response_events(with_deltas=with_deltas))


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
        mock_credential = MagicMock()
        mock_credential.__aenter__ = AsyncMock(return_value=mock_credential)
        mock_credential.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.service.get_credentials",
                return_value=mock_credential,
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
        mock_credential.__aenter__.assert_awaited()
        mock_credential.__aexit__.assert_awaited()
        mock_client.__aenter__.assert_awaited()
        mock_client.__aexit__.assert_awaited()

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
        stream = _fake_response_stream()
        mock_openai.responses.create = AsyncMock(
            side_effect=[missing, stream],
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
        assert stream.closed is True

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

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_stream_empty_agent_name_allows_create_on_miss(
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
            side_effect=[missing, _fake_response_stream()],
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
                    agent_name="",
                )
            ]

        assert chunks[0][0] == "agent answer text"
        mock_client.agents.create_version.assert_awaited_once()
        assert mock_openai.responses.create.await_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_stream_falls_back_to_completed_output_text(
        self, bing_env: None
    ) -> None:
        stream = _fake_response_stream(with_deltas=False)
        mock_openai = MagicMock()
        mock_openai.responses.create = AsyncMock(
            return_value=stream,
        )
        mock_client = MagicMock()

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
                    agent_name="existing-agent",
                )
            ]

        assert len(chunks) == 1
        assert chunks[0][0] == "agent answer text"
        assert chunks[0][1]["type"] == "response.completed"
        assert stream.closed is True


class TestPrivateEndpointHttpClientReuse:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_private_endpoint_reuses_shared_httpx_client(
        self, bing_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BING_AGENT_USE_PRIVATE_ENDPOINT_TRANSPORT", "true")
        from unique_search_proxy_client.web.settings.providers import bing_agent

        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.agent_engines.bing.client.bing_agent_credentials",
            bing_agent._get_bing_agent_credentials(),
        )
        await aclose_private_endpoint_http_client()
        project_client = MagicMock()
        project_client.get_openai_client = MagicMock(return_value=MagicMock())

        get_openai_client_from_client_module(project_client)
        get_openai_client_from_client_module(project_client)

        first = project_client.get_openai_client.call_args_list[0].kwargs["http_client"]
        second = project_client.get_openai_client.call_args_list[1].kwargs[
            "http_client"
        ]
        assert first is second
        await aclose_private_endpoint_http_client()


class TestCleanupAutoProvisionedBingAgents:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_deletes_only_prefix_matching_agents(self) -> None:
        keep = MagicMock(name="manual-agent")
        keep.name = "manual-agent"
        delete_me = MagicMock(name="hashed")
        delete_me.name = f"{BING_AUTO_AGENT_NAME_PREFIX}-abc123def456"
        also_keep = MagicMock(name="other-prefix")
        also_keep.name = "unique-other-agent-xyz"

        async def _agents() -> AsyncIterator[Any]:
            for agent in (keep, delete_me, also_keep):
                yield agent

        project_client = MagicMock()
        project_client.agents.list = MagicMock(return_value=_agents())
        project_client.agents.delete = AsyncMock()

        deleted = await cleanup_auto_provisioned_bing_agents(project_client)

        assert deleted == 1
        project_client.agents.delete.assert_awaited_once_with(delete_me.name)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_continues_when_one_delete_fails(self) -> None:
        first = MagicMock()
        first.name = f"{BING_AUTO_AGENT_NAME_PREFIX}-one"
        second = MagicMock()
        second.name = f"{BING_AUTO_AGENT_NAME_PREFIX}-two"

        async def _agents() -> AsyncIterator[Any]:
            yield first
            yield second

        project_client = MagicMock()
        project_client.agents.list = MagicMock(return_value=_agents())
        project_client.agents.delete = AsyncMock(
            side_effect=[RuntimeError("boom"), None],
        )

        deleted = await cleanup_auto_provisioned_bing_agents(project_client)

        assert deleted == 1
        assert project_client.agents.delete.await_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_maybe_cleanup_swallows_top_level_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Purpose: Verify startup cleanup never raises into FastAPI lifespan.
        Why this matters: Multi-worker/replica races must not block process start.
        Setup summary: Force credential check to pass, then fail client setup; assert no raise.
        """
        creds = MagicMock()
        creds.cleanup_on_start = True
        creds.endpoint = MagicMock()
        creds.check_credentials = MagicMock()
        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.agent_engines.bing.cleanup.bing_agent_credentials",
            creds,
        )
        with (
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.cleanup.get_credentials",
                side_effect=RuntimeError("credential boom"),
            ),
            patch(
                "unique_search_proxy_client.web.core.agent_engines.bing.cleanup.read_secret",
                return_value="https://example.azure.com",
            ),
        ):
            await maybe_cleanup_auto_provisioned_bing_agents_on_start()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_maybe_cleanup_skips_when_setting_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        creds = MagicMock()
        creds.cleanup_on_start = False
        monkeypatch.setattr(
            "unique_search_proxy_client.web.core.agent_engines.bing.cleanup.bing_agent_credentials",
            creds,
        )
        with patch(
            "unique_search_proxy_client.web.core.agent_engines.bing.cleanup.get_project_client",
        ) as get_client:
            await maybe_cleanup_auto_provisioned_bing_agents_on_start()
            get_client.assert_not_called()
            creds.check_credentials.assert_not_called()
