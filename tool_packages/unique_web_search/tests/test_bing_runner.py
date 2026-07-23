"""Tests for Bing grounding agent runner, models, and response parsing strategies."""

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import NotFoundError
from openai.types.responses.response import Response
from openai.types.responses.response_completed_event import ResponseCompletedEvent
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from openai.types.responses.response_usage import ResponseUsage
from pydantic import ValidationError

from unique_web_search.invocation_stats import invocation_stats_scope
from unique_web_search.services.search_engine.schema import (
    WebSearchResult,
)
from unique_web_search.services.search_engine.utils.grounding import (
    JsonConversionStrategy,
    LLMParserStrategy,
)
from unique_web_search.services.search_engine.utils.grounding.bing.models import (
    GENERATION_INSTRUCTIONS,
    RESPONSE_RULE,
    GroundingWithBingResults,
    ResultItem,
)
from unique_web_search.services.search_engine.utils.grounding.bing.runner import (
    _agent_name_for_config,
    _config_hash,
    _is_missing_agent_error,
    create_and_process_run,
    create_bing_agent,
    get_bing_grounding_tool,
    get_or_create_agent_id,
    resolve_bing_agent_name,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _async_iter(items: list) -> AsyncIterator:
    """Wrap a list as an async iterator for mocking async-for-compatible APIs."""
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_result_item() -> ResultItem:
    """A single ResultItem for reuse across tests."""
    return ResultItem(
        source_url="https://example.com/article",
        source_title="Example Article",
        detailed_answer="Full detailed answer with facts and figures.",
        key_facts=["Fact A", "Fact B", "Fact C"],
    )


@pytest.fixture
def sample_grounding_results(
    sample_result_item: ResultItem,
) -> GroundingWithBingResults:
    """GroundingWithBingResults with two items."""
    second = ResultItem(
        source_url="https://other.com/page",
        source_title="Other Page",
        detailed_answer="Another detailed answer.",
        key_facts=["Fact X"],
    )
    return GroundingWithBingResults(results=[sample_result_item, second])


@pytest.fixture
def valid_json_response(sample_grounding_results: GroundingWithBingResults) -> str:
    """Agent response containing a valid fenced JSON block."""
    json_body = sample_grounding_results.model_dump_json()
    return f"Here are the results:\n```json\n{json_body}\n```\n"


@pytest.fixture
def mock_agent_client() -> MagicMock:
    """Mock AIProjectClient with nested agents/messages stubs."""
    client = MagicMock()
    client.agents = MagicMock()
    client.agents.messages = MagicMock()
    return client


# ---------------------------------------------------------------------------
# GroundingWithBingResults model tests
# ---------------------------------------------------------------------------


class TestGroundingWithBingResults:
    """Tests for the GroundingWithBingResults Pydantic model."""

    @pytest.mark.ai
    def test_to_web_search_results__maps_fields_correctly__single_item(
        self, sample_result_item: ResultItem
    ) -> None:
        """
        Purpose: Verify to_web_search_results maps ResultItem fields to WebSearchResult.
        Why this matters: Incorrect mapping silently produces wrong search results.
        Setup summary: Single ResultItem; assert url, title, snippet, and content.
        """
        # Arrange
        grounding = GroundingWithBingResults(results=[sample_result_item])

        # Act
        web_results = grounding.to_web_search_results()

        # Assert
        assert len(web_results) == 1
        result = web_results[0]
        assert result.url == "https://example.com/article"
        assert result.title == "Example Article"
        assert result.content == "Full detailed answer with facts and figures."
        assert result.snippet == "Fact A\nFact B\nFact C"

    @pytest.mark.ai
    def test_to_web_search_results__joins_key_facts__into_snippet(self) -> None:
        """
        Purpose: Verify key_facts are joined with newline as snippet.
        Why this matters: Snippet display relies on correct delimiter.
        Setup summary: ResultItem with multiple key_facts; assert newline-joined snippet.
        """
        # Arrange
        item = ResultItem(
            source_url="https://a.com",
            source_title="A",
            detailed_answer="Details",
            key_facts=["one", "two", "three"],
        )
        grounding = GroundingWithBingResults(results=[item])

        # Act
        web_results = grounding.to_web_search_results()

        # Assert
        assert web_results[0].snippet == "one\ntwo\nthree"

    @pytest.mark.ai
    def test_to_web_search_results__empty_results__returns_empty_list(self) -> None:
        """
        Purpose: Verify empty results list produces empty output.
        Why this matters: Prevents IndexError or unexpected behavior on empty input.
        Setup summary: GroundingWithBingResults with no items.
        """
        # Arrange
        grounding = GroundingWithBingResults(results=[])

        # Act
        web_results = grounding.to_web_search_results()

        # Assert
        assert web_results == []

    @pytest.mark.ai
    def test_to_web_search_results__multiple_items__preserves_order(
        self, sample_grounding_results: GroundingWithBingResults
    ) -> None:
        """
        Purpose: Verify multiple items are converted in order.
        Why this matters: Result ordering affects display ranking.
        Setup summary: Two ResultItems; assert both converted and order preserved.
        """
        # Act
        web_results = sample_grounding_results.to_web_search_results()

        # Assert
        assert len(web_results) == 2
        assert web_results[0].url == "https://example.com/article"
        assert web_results[1].url == "https://other.com/page"

    @pytest.mark.ai
    def test_result_item__rejects_extra_fields__with_forbid(self) -> None:
        """
        Purpose: Verify ResultItem rejects unknown fields due to extra='forbid'.
        Why this matters: Prevents silent acceptance of malformed data from the agent.
        Setup summary: Create ResultItem with an extra field; assert ValidationError.
        """
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            ResultItem(
                source_url="https://a.com",
                source_title="A",
                detailed_answer="Details",
                key_facts=["fact"],
                unknown_field="should fail",
            )
        assert "extra_forbidden" in str(exc_info.value)

    @pytest.mark.ai
    def test_grounding_results__rejects_extra_fields__with_forbid(self) -> None:
        """
        Purpose: Verify GroundingWithBingResults rejects unknown fields due to extra='forbid'.
        Why this matters: Prevents silent acceptance of malformed structured output.
        Setup summary: Create GroundingWithBingResults with an extra field; assert ValidationError.
        """
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            GroundingWithBingResults(
                results=[],
                unknown_field="should fail",
            )
        assert "extra_forbidden" in str(exc_info.value)


# ---------------------------------------------------------------------------
# JsonConversionStrategy tests
# ---------------------------------------------------------------------------


class TestJsonConversionStrategy:
    """Tests for the JSON code-fence extraction strategy."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__valid_json_fence__returns_web_search_results(
        self, valid_json_response: str
    ) -> None:
        """
        Purpose: Verify valid fenced JSON is parsed into WebSearchResult list.
        Why this matters: Primary parsing path must work for normal agent responses.
        Setup summary: Response with ```json block; assert correct number of results.
        """
        # Arrange
        strategy = JsonConversionStrategy()

        # Act
        results = await strategy(valid_json_response)

        # Assert
        assert len(results) == 2
        assert isinstance(results[0], WebSearchResult)
        assert results[0].url == "https://example.com/article"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__no_json_fence__raises_value_error(self) -> None:
        """
        Purpose: Verify ValueError is raised when no JSON code fence exists.
        Why this matters: Enables fallback to next strategy in the chain.
        Setup summary: Plain text response without code fence.
        """
        # Arrange
        strategy = JsonConversionStrategy()
        response = "This is a plain text answer without any JSON."

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await strategy(response)
        assert "No JSON found" in str(exc_info.value)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__malformed_json__raises_validation_error(self) -> None:
        """
        Purpose: Verify malformed JSON inside code fence raises an error.
        Why this matters: Corrupt output must not silently produce partial results.
        Setup summary: Response with invalid JSON in code fence.
        """
        # Arrange
        strategy = JsonConversionStrategy()
        response = '```json\n{"results": [{"invalid": true}]}\n```'

        # Act & Assert
        with pytest.raises(Exception):
            await strategy(response)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__json_with_surrounding_text__extracts_correctly(
        self, sample_result_item: ResultItem
    ) -> None:
        """
        Purpose: Verify JSON extraction works even with surrounding prose.
        Why this matters: Agent responses often include text before/after JSON.
        Setup summary: Response with preamble and postamble around JSON fence.
        """
        # Arrange
        strategy = JsonConversionStrategy()
        grounding = GroundingWithBingResults(results=[sample_result_item])
        response = (
            "I found the following results:\n"
            f"```json\n{grounding.model_dump_json()}\n```\n"
            "Hope this helps!"
        )

        # Act
        results = await strategy(response)

        # Assert
        assert len(results) == 1
        assert results[0].title == "Example Article"


# ---------------------------------------------------------------------------
# LLMParserStrategy tests
# ---------------------------------------------------------------------------


class TestLLMParserStrategy:
    """Tests for the LLM-based fallback parsing strategy."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__successful_parse__returns_results(self) -> None:
        """
        Purpose: Verify LLM parser returns structured results on success.
        Why this matters: Fallback parser must produce correct WebSearchResult objects.
        Setup summary: Mock LLM service to return valid parsed GroundingWithBingResults output.
        """
        # Arrange
        mock_lmi = MagicMock()
        mock_lmi.name = "gpt-4o"
        mock_service = MagicMock()

        parsed_data = GroundingWithBingResults(
            results=[
                ResultItem(
                    source_url="https://llm-parsed.com",
                    source_title="LLM Parsed",
                    detailed_answer="Parsed content",
                    key_facts=["Parsed snippet"],
                )
            ]
        )
        mock_choice = MagicMock()
        mock_choice.message.parsed = parsed_data.model_dump()
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_service.complete_async = AsyncMock(return_value=mock_response)

        strategy = LLMParserStrategy(llm=mock_lmi, llm_service=mock_service)

        # Act
        results = await strategy("Some unstructured agent response text")

        # Assert
        assert len(results) == 1
        assert results[0].url == "https://llm-parsed.com"
        assert results[0].title == "LLM Parsed"
        mock_service.complete_async.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__no_parsed_content__raises_value_error(self) -> None:
        """
        Purpose: Verify ValueError when LLM returns no parsed content.
        Why this matters: Signals strategy failure so orchestrator can report properly.
        Setup summary: Mock LLM service to return None as parsed.
        """
        # Arrange
        mock_lmi = MagicMock()
        mock_lmi.name = "gpt-4o"
        mock_service = MagicMock()

        mock_choice = MagicMock()
        mock_choice.message.parsed = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_service.complete_async = AsyncMock(return_value=mock_response)

        strategy = LLMParserStrategy(llm=mock_lmi, llm_service=mock_service)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await strategy("Some text")
        assert "No JSON found" in str(exc_info.value)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_call__passes_correct_params__to_llm_service(self) -> None:
        """
        Purpose: Verify LLM service is called with structured_output_model and enforce_schema.
        Why this matters: Ensures schema enforcement is active for reliable parsing.
        Setup summary: Mock service; inspect call kwargs after invocation.
        """
        # Arrange
        mock_lmi = MagicMock()
        mock_lmi.name = "test-model"
        mock_service = MagicMock()

        parsed_data = GroundingWithBingResults(
            results=[
                ResultItem(
                    source_url="https://a.com",
                    source_title="A",
                    detailed_answer="c",
                    key_facts=["s"],
                )
            ]
        )
        mock_choice = MagicMock()
        mock_choice.message.parsed = parsed_data.model_dump()
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_service.complete_async = AsyncMock(return_value=mock_response)

        strategy = LLMParserStrategy(llm=mock_lmi, llm_service=mock_service)

        # Act
        await strategy("response text")

        # Assert
        call_kwargs = mock_service.complete_async.call_args[1]
        assert call_kwargs["model_name"] == "test-model"
        assert call_kwargs["structured_output_model"] is GroundingWithBingResults
        assert call_kwargs["structured_output_enforce_schema"] is True


# ---------------------------------------------------------------------------
# Agent naming / create_bing_agent / get_or_create_agent_id tests
# ---------------------------------------------------------------------------


class TestConfigHashAndAgentName:
    """Tests for hash-based Bing agent naming."""

    @pytest.mark.ai
    def test_same_inputs__produce_same_hash_and_name(self) -> None:
        """
        Purpose: Verify hash and agent name are stable for identical inputs.
        Why this matters: Stable names enable Responses-first reuse without agents.get.
        Setup summary: Hash twice with same model/fetch_size/instructions; assert equality.
        """
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
    def test_different_fetch_size_or_instructions__change_name(self) -> None:
        """
        Purpose: Verify fetch_size and instructions both affect the derived name.
        Why this matters: Different Bing configs must not share an agent version.
        Setup summary: Vary one input at a time; assert distinct names.
        """
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

    @pytest.mark.ai
    def test_different_model__changes_name(self) -> None:
        """
        Purpose: Verify model is included in the agent hash.
        Why this matters: Model is baked into the Foundry agent; changing deployment
            must create a new hashed agent instead of reusing the old one.
        Setup summary: Same fetch_size/instructions, different model; assert distinct names.
        """
        base = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions="Be helpful."
        )
        other_model = _agent_name_for_config(
            model="gpt-4o", fetch_size=5, instructions="Be helpful."
        )
        assert base != other_model

    @pytest.mark.ai
    @patch(
        "unique_web_search.services.search_engine.utils.grounding.bing.runner.env_settings"
    )
    def test_resolve__prefers_preconfigured_name(self, mock_env: MagicMock) -> None:
        """
        Purpose: Verify explicit agent_name wins over hash derivation.
        Why this matters: Admins can pin a known Foundry agent.
        Setup summary: Pass agent_name; assert returned unchanged.
        """
        mock_env.azure_ai_assistant_id = None
        assert (
            resolve_bing_agent_name(
                model="gpt-5.1",
                fetch_size=5,
                instructions="Be helpful.",
                agent_name="my-agent",
            )
            == "my-agent"
        )


class TestCreateBingAgent:
    """Tests for agent version creation logic (SDK 2.x)."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(
        "unique_web_search.services.search_engine.utils.grounding.bing.runner.env_settings"
    )
    async def test_create__bakes_instructions_into_definition(
        self, mock_env: MagicMock, mock_agent_client: MagicMock
    ) -> None:
        """
        Purpose: Verify create_version is called with per-request instructions baked in.
        Why this matters: Foundry rejects instructions on responses.create with agent_reference.
        Setup summary: Mock create_version; assert instructions land on PromptAgentDefinition.
        """
        mock_env.azure_ai_assistant_id = None
        mock_env.azure_ai_bing_agent_model = "gpt-5.1"
        mock_env.azure_ai_bing_resource_connection_string = (
            "/subscriptions/x/connections/bing"
        )
        expected_name = _agent_name_for_config(
            model="gpt-5.1",
            fetch_size=5,
            instructions="Be helpful.\n## Output Format",
        )
        new_agent = MagicMock()
        new_agent.name = expected_name
        new_agent.id = "new-agent-456"
        mock_agent_client.agents.create_version = AsyncMock(return_value=new_agent)

        agent_name = await create_bing_agent(
            mock_agent_client,
            agent_name=expected_name,
            model="gpt-5.1",
            fetch_size=5,
            instructions="Be helpful.\n## Output Format",
        )

        assert agent_name == expected_name
        mock_agent_client.agents.create_version.assert_called_once()
        call_kwargs = mock_agent_client.agents.create_version.call_args.kwargs
        assert call_kwargs["agent_name"] == expected_name
        assert call_kwargs["definition"].instructions == "Be helpful.\n## Output Format"

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(
        "unique_web_search.services.search_engine.utils.grounding.bing.runner.env_settings"
    )
    async def test_get_or_create__env_assistant_id_set__returns_env_id_directly(
        self, mock_env: MagicMock, mock_agent_client: MagicMock
    ) -> None:
        """
        Purpose: Verify env-set assistant_id is returned immediately without agent lookup.
        Why this matters: IT admins setting the assistant_id in .env expect it to be used
            directly, bypassing auto-provisioning entirely.
        Setup summary: Set azure_ai_assistant_id on env; assert returned without create_version.
        """
        mock_env.azure_ai_assistant_id = "env-preconfigured-agent-id"

        agent_name = await get_or_create_agent_id(mock_agent_client)

        assert agent_name == "env-preconfigured-agent-id"
        mock_agent_client.agents.create_version.assert_not_called()


class TestMissingAgentError:
    """Tests for missing-agent error detection."""

    @pytest.mark.ai
    def test_detects_openai_not_found(self) -> None:
        """
        Purpose: Verify NotFoundError is treated as a missing agent.
        Why this matters: Optimistic Responses-first flow must create only on miss.
        Setup summary: Build NotFoundError; assert detector returns True.
        """
        exc = NotFoundError(
            message="Agent unique-grounding-with-bing-abc not found",
            response=MagicMock(status_code=404, headers={}),
            body=None,
        )
        assert _is_missing_agent_error(exc, agent_name="unique-grounding-with-bing-abc")


# ---------------------------------------------------------------------------
# get_bing_grounding_tool tests
# ---------------------------------------------------------------------------


class TestGetBingGroundingTool:
    """Tests for BingGroundingTool factory function."""

    @pytest.mark.ai
    @patch(
        "unique_web_search.services.search_engine.utils.grounding.bing.runner.env_settings"
    )
    def test_get_tool__connection_string_set__returns_nested_config(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify BingGroundingTool is created with project_connection_id and count.
        Why this matters: Tool must be properly configured for agent runs under SDK 2.x.
        Setup summary: Set connection string; assert nested search configuration fields.
        """
        mock_env.azure_ai_bing_resource_connection_string = (
            "projects/123/connections/bing"
        )

        tool = get_bing_grounding_tool(fetch_size=10)

        configs = tool.bing_grounding.search_configurations
        assert len(configs) == 1
        assert configs[0].project_connection_id == "projects/123/connections/bing"
        assert configs[0].count == 10

    @pytest.mark.ai
    @patch(
        "unique_web_search.services.search_engine.utils.grounding.bing.runner.env_settings"
    )
    def test_get_tool__connection_string_missing__raises_value_error(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify ValueError when Bing connection string is not set.
        Why this matters: Clear error prevents silent failures in agent runs.
        Setup summary: Set connection string to None; assert ValueError raised.
        """
        mock_env.azure_ai_bing_resource_connection_string = None

        with pytest.raises(ValueError) as exc_info:
            get_bing_grounding_tool(fetch_size=5)
        assert "Connection String is not set" in str(exc_info.value)

    @pytest.mark.ai
    @patch(
        "unique_web_search.services.search_engine.utils.grounding.bing.runner.env_settings"
    )
    def test_get_tool__empty_connection_string__raises_value_error(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify ValueError when connection string is empty string.
        Why this matters: Empty string should be treated same as missing.
        Setup summary: Set connection string to empty; assert ValueError raised.
        """
        mock_env.azure_ai_bing_resource_connection_string = ""

        with pytest.raises(ValueError):
            get_bing_grounding_tool(fetch_size=5)


# ---------------------------------------------------------------------------
# create_and_process_run tests
# ---------------------------------------------------------------------------


_RUNNER_MODULE = "unique_web_search.services.search_engine.utils.grounding.bing.runner"


async def _fake_response_stream(
    *,
    usage: ResponseUsage | None = None,
) -> AsyncIterator:
    yield ResponseTextDeltaEvent.model_construct(
        type="response.output_text.delta",
        delta="response text",
        content_index=0,
        item_id="item-1",
        output_index=0,
        sequence_number=1,
        logprobs=[],
    )
    text = ResponseOutputText.model_construct(
        type="output_text",
        text="response text",
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
        usage=usage,
    )
    yield ResponseCompletedEvent.model_construct(
        type="response.completed",
        sequence_number=2,
        response=response,
    )


def _mock_openai_client(
    *,
    usage: ResponseUsage | None = None,
) -> MagicMock:
    mock_openai = MagicMock()
    mock_openai.responses.create = AsyncMock(
        side_effect=lambda *_a, **_k: _fake_response_stream(usage=usage),
    )
    return mock_openai


class TestCreateAndProcessRun:
    """Tests for the main Bing agent run orchestration (Responses API)."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__successful_without_agent_id__returns_parsed_results(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify successful run returns parsed search results when no agent_id is provided.
        Why this matters: Core happy-path for Bing grounding with hash-based agent reuse.
        Setup summary: Mock Responses stream (agent already exists); assert parser is invoked
            and create_version is not called.
        """
        mock_env.azure_ai_assistant_id = None
        mock_env.azure_ai_bing_agent_model = "gpt-5.1"
        mock_env.azure_ai_bing_resource_connection_string = (
            "/subscriptions/x/connections/bing"
        )
        mock_agent_client = MagicMock()
        mock_agent_client.agents.create_version = AsyncMock()
        expected_results = [
            WebSearchResult(url="https://a.com", title="A", snippet="s", content="c")
        ]
        mock_parser = AsyncMock(return_value=expected_results)

        with patch(
            f"{_RUNNER_MODULE}.get_openai_client",
            return_value=_mock_openai_client(),
        ):
            results = await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="",
                query="test query",
                fetch_size=5,
                response_parsers_strategies=[mock_parser],
                generation_instructions="Test instructions",
            )

        assert results == expected_results
        mock_agent_client.agents.create_version.assert_not_called()
        mock_parser.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__completed_response__records_token_usage(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify Responses completion usage is recorded for billing/observability.
        Why this matters: Replaces Threads ``thread.usage`` recording after the SDK migration.
        Setup summary: Stream a completed response with ResponseUsage inside invocation_stats_scope.
        """
        mock_env.azure_ai_assistant_id = None
        mock_env.azure_ai_bing_agent_model = "gpt-5.1"
        mock_env.azure_ai_bing_resource_connection_string = (
            "/subscriptions/x/connections/bing"
        )
        mock_agent_client = MagicMock()
        mock_agent_client.agents.create_version = AsyncMock()
        mock_parser = AsyncMock(
            return_value=[
                WebSearchResult(
                    url="https://a.com", title="A", snippet="s", content="c"
                )
            ]
        )
        usage = ResponseUsage.model_construct(
            input_tokens=12,
            output_tokens=34,
            total_tokens=46,
            input_tokens_details=None,
            output_tokens_details=None,
        )

        with (
            patch(
                f"{_RUNNER_MODULE}.get_openai_client",
                return_value=_mock_openai_client(usage=usage),
            ),
            invocation_stats_scope() as invocation_stats,
        ):
            await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="",
                query="test query",
                fetch_size=5,
                response_parsers_strategies=[mock_parser],
                generation_instructions="Test instructions",
            )

        assert len(invocation_stats) == 1
        assert invocation_stats[0].model_name == "gpt-5.1"
        assert invocation_stats[0].source == "web_search.grounding.bing"
        assert invocation_stats[0].token_usage.prompt_tokens == 12
        assert invocation_stats[0].token_usage.completion_tokens == 34
        assert invocation_stats[0].token_usage.total_tokens == 46

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__with_agent_id__uses_existing_agent(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify that providing an agent_id skips auto-create and uses the given name.
        Why this matters: Allows using pre-configured agents from config without auto-provisioning.
        Setup summary: Provide non-empty agent_id; assert Responses uses it and create is skipped.
        """
        mock_env.azure_ai_assistant_id = None
        mock_agent_client = MagicMock()
        mock_agent_client.agents.create_version = AsyncMock()
        expected_results = [
            WebSearchResult(
                url="https://existing.com", title="E", snippet="s", content="c"
            )
        ]
        mock_parser = AsyncMock(return_value=expected_results)
        mock_openai = _mock_openai_client()

        with patch(
            f"{_RUNNER_MODULE}.get_openai_client",
            return_value=mock_openai,
        ):
            results = await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="pre-configured-agent-id",
                query="test query",
                fetch_size=5,
                response_parsers_strategies=[mock_parser],
                generation_instructions="Test instructions",
            )

        assert results == expected_results
        mock_agent_client.agents.create_version.assert_not_called()
        create_kwargs = mock_openai.responses.create.await_args.kwargs
        assert (
            create_kwargs["extra_body"]["agent_reference"]["name"]
            == "pre-configured-agent-id"
        )
        mock_parser.assert_called_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__missing_hashed_agent__creates_then_retries(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify missing hash-named agent triggers create_version then Responses retry.
        Why this matters: Optimistic Responses-first flow must provision only on miss.
        Setup summary: First Responses raises NotFoundError; second succeeds; assert one create.
        """
        mock_env.azure_ai_assistant_id = None
        mock_env.azure_ai_bing_agent_model = "gpt-5.1"
        mock_env.azure_ai_bing_resource_connection_string = (
            "/subscriptions/x/connections/bing"
        )
        instructions = f"Test instructions\n{RESPONSE_RULE}"
        expected_name = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions=instructions
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
        mock_agent_client = MagicMock()
        mock_agent_client.agents.create_version = AsyncMock(return_value=created)
        expected_results = [
            WebSearchResult(url="https://a.com", title="A", snippet="s", content="c")
        ]
        mock_parser = AsyncMock(return_value=expected_results)

        with patch(
            f"{_RUNNER_MODULE}.get_openai_client",
            return_value=mock_openai,
        ):
            results = await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="",
                query="test query",
                fetch_size=5,
                response_parsers_strategies=[mock_parser],
                generation_instructions="Test instructions",
            )

        assert results == expected_results
        mock_agent_client.agents.create_version.assert_awaited_once()
        assert mock_openai.responses.create.await_count == 2

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__missing_preconfigured_agent__does_not_create(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify preconfigured agent miss is not auto-created.
        Why this matters: Explicit agent names must fail loudly, not silently provision.
        Setup summary: agent_id set; Responses raises NotFoundError; assert no create_version.
        """
        mock_env.azure_ai_assistant_id = None
        missing = NotFoundError(
            message="Agent my-preconfigured-agent not found",
            response=MagicMock(status_code=404, headers={}),
            body=None,
        )
        mock_openai = MagicMock()
        mock_openai.responses.create = AsyncMock(side_effect=missing)
        mock_agent_client = MagicMock()
        mock_agent_client.agents.create_version = AsyncMock()

        with (
            patch(
                f"{_RUNNER_MODULE}.get_openai_client",
                return_value=mock_openai,
            ),
            pytest.raises(NotFoundError),
        ):
            await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="my-preconfigured-agent",
                query="test query",
                fetch_size=5,
                response_parsers_strategies=[AsyncMock()],
                generation_instructions="Test instructions",
            )

        mock_agent_client.agents.create_version.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__empty_agent_id__allows_create_on_miss(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify empty agent_id is treated as unset and still auto-provisions.
        Why this matters: Schema says empty id auto-provisions; "" must not block create.
        Setup summary: agent_id=""; first Responses misses; assert create_version once.
        """
        mock_env.azure_ai_assistant_id = None
        mock_env.azure_ai_bing_agent_model = "gpt-5.1"
        mock_env.azure_ai_bing_resource_connection_string = (
            "/subscriptions/x/connections/bing"
        )
        instructions = f"Test instructions\n{RESPONSE_RULE}"
        expected_name = _agent_name_for_config(
            model="gpt-5.1", fetch_size=5, instructions=instructions
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
        mock_agent_client = MagicMock()
        mock_agent_client.agents.create_version = AsyncMock(return_value=created)
        expected_results = [
            WebSearchResult(url="https://a.com", title="A", snippet="s", content="c")
        ]
        mock_parser = AsyncMock(return_value=expected_results)

        with patch(
            f"{_RUNNER_MODULE}.get_openai_client",
            return_value=mock_openai,
        ):
            results = await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="",
                query="test query",
                fetch_size=5,
                response_parsers_strategies=[mock_parser],
                generation_instructions="Test instructions",
            )

        assert results == expected_results
        mock_agent_client.agents.create_version.assert_awaited_once()

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__all_parsers_fail__raises_value_error(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify ValueError when no parser can handle the response.
        Why this matters: Callers need a definitive signal that parsing failed.
        Setup summary: Mock Responses stream succeeds but all parsers raise; assert ValueError.
        """
        mock_env.azure_ai_assistant_id = None
        mock_agent_client = MagicMock()
        failing_parser = AsyncMock(side_effect=ValueError("cannot parse"))

        with patch(
            f"{_RUNNER_MODULE}.get_openai_client",
            return_value=_mock_openai_client(),
        ):
            with pytest.raises(ValueError) as exc_info:
                await create_and_process_run(
                    agent_client=mock_agent_client,
                    agent_id="",
                    query="test",
                    fetch_size=5,
                    response_parsers_strategies=[failing_parser],
                    generation_instructions="instructions",
                )
            assert "No conversion strategy found" in str(exc_info.value)

    @pytest.mark.ai
    @pytest.mark.asyncio
    @patch(f"{_RUNNER_MODULE}.env_settings")
    async def test_run__first_parser_fails__second_succeeds(
        self,
        mock_env: MagicMock,
    ) -> None:
        """
        Purpose: Verify fallback to second parser when first fails during a run.
        Why this matters: Validates the full strategy chain within create_and_process_run.
        Setup summary: First parser raises; second returns results; assert success.
        """
        mock_env.azure_ai_assistant_id = None
        mock_agent_client = MagicMock()
        expected = [
            WebSearchResult(url="https://fb.com", title="FB", snippet="s", content="c")
        ]
        parser_1 = AsyncMock(side_effect=ValueError("nope"))
        parser_2 = AsyncMock(return_value=expected)

        with patch(
            f"{_RUNNER_MODULE}.get_openai_client",
            return_value=_mock_openai_client(),
        ):
            results = await create_and_process_run(
                agent_client=mock_agent_client,
                agent_id="",
                query="query",
                fetch_size=3,
                response_parsers_strategies=[parser_1, parser_2],
                generation_instructions="instructions",
            )

        assert results == expected
        parser_1.assert_called_once()
        parser_2.assert_called_once()


# ---------------------------------------------------------------------------
# BingSearchConfig tests
# ---------------------------------------------------------------------------


class TestBingSearchConfig:
    """Tests for BingSearchConfig defaults and field values."""

    @pytest.mark.ai
    def test_config__default_values__set_correctly(self) -> None:
        """
        Purpose: Verify BingSearchConfig has correct default field values.
        Why this matters: Misconfigured defaults break zero-config deployments.
        Setup summary: Create config with no overrides; assert defaults.
        """
        from unique_web_search.services.search_engine.bing import BingSearchConfig

        # Act
        config = BingSearchConfig()

        # Assert
        assert config.engine == "bing"
        assert config.requires_scraping is False
        assert config.fetch_size == 5
        assert config.generation_instructions == GENERATION_INSTRUCTIONS
        assert config.language_model is not None

    @pytest.mark.ai
    def test_config__custom_generation_instructions__override_default(self) -> None:
        """
        Purpose: Verify generation_instructions can be overridden.
        Why this matters: Customers may need to customize agent behavior.
        Setup summary: Provide custom instructions; assert stored correctly.
        """
        from unique_web_search.services.search_engine.bing import BingSearchConfig

        # Arrange
        custom = "Custom instructions for testing."

        # Act
        config = BingSearchConfig(generation_instructions=custom)

        # Assert
        assert config.generation_instructions == custom

    @pytest.mark.ai
    def test_config__agent_id_and_endpoint__default_to_empty_string(self) -> None:
        """
        Purpose: Verify agent_id and endpoint default to empty strings.
        Why this matters: Empty defaults enable auto-provisioning fallback path.
        Setup summary: Create config with no overrides; assert agent_id and endpoint are "".
        """
        from unique_web_search.services.search_engine.bing import BingSearchConfig

        # Act
        config = BingSearchConfig()

        # Assert
        assert config.agent_id == ""
        assert config.endpoint == ""

    @pytest.mark.ai
    def test_config__custom_agent_id_and_endpoint__stored_correctly(self) -> None:
        """
        Purpose: Verify agent_id and endpoint can be overridden with custom values.
        Why this matters: Allows pre-configured agent usage from deployment config.
        Setup summary: Provide custom agent_id and endpoint; assert stored correctly.
        """
        from unique_web_search.services.search_engine.bing import BingSearchConfig

        # Act
        config = BingSearchConfig(
            agent_id="my-agent-id-123",
            endpoint="https://my-project.azure.com",
        )

        # Assert
        assert config.agent_id == "my-agent-id-123"
        assert config.endpoint == "https://my-project.azure.com"

    @pytest.mark.ai
    @patch("unique_web_search.services.search_engine.bing.env_settings")
    def test_config__agent_id_defaults_from_env__when_env_set(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify agent_id defaults to env_settings.azure_ai_assistant_id when set.
        Why this matters: IT admins setting the assistant_id in .env expect BingSearchConfig
            to pick it up automatically without explicit config.
        Setup summary: Patch env_settings with assistant_id; create config without override; assert match.
        """
        from unique_web_search.services.search_engine.bing import BingSearchConfig

        # Arrange
        mock_env.azure_ai_assistant_id = "env-agent-abc"
        mock_env.azure_ai_project_endpoint = None

        # Act
        config = BingSearchConfig(
            agent_id=mock_env.azure_ai_assistant_id or "",
            endpoint=mock_env.azure_ai_project_endpoint or "",
        )

        # Assert
        assert config.agent_id == "env-agent-abc"

    @pytest.mark.ai
    @patch("unique_web_search.services.search_engine.bing.env_settings")
    def test_config__endpoint_defaults_from_env__when_env_set(
        self, mock_env: MagicMock
    ) -> None:
        """
        Purpose: Verify endpoint defaults to env_settings.azure_ai_project_endpoint when set.
        Why this matters: IT admins setting the endpoint in .env expect BingSearchConfig
            to pick it up automatically without explicit config.
        Setup summary: Patch env_settings with endpoint; create config without override; assert match.
        """
        from unique_web_search.services.search_engine.bing import BingSearchConfig

        # Arrange
        mock_env.azure_ai_assistant_id = None
        mock_env.azure_ai_project_endpoint = "https://env-endpoint.azure.com"

        # Act
        config = BingSearchConfig(
            agent_id=mock_env.azure_ai_assistant_id or "",
            endpoint=mock_env.azure_ai_project_endpoint or "",
        )

        # Assert
        assert config.endpoint == "https://env-endpoint.azure.com"


# ---------------------------------------------------------------------------
# Models constants tests
# ---------------------------------------------------------------------------


class TestModelsConstants:
    """Tests for prompt constants in models.py."""

    @pytest.mark.ai
    def test_generation_instructions__is_non_empty_string(self) -> None:
        """
        Purpose: Verify GENERATION_INSTRUCTIONS is a non-empty string.
        Why this matters: Empty instructions would produce useless agent behavior.
        Setup summary: Import constant; assert non-empty.
        """
        assert isinstance(GENERATION_INSTRUCTIONS, str)
        assert len(GENERATION_INSTRUCTIONS) > 0
        assert "Expert Web Research Agent" in GENERATION_INSTRUCTIONS

    @pytest.mark.ai
    def test_response_rule__contains_json_schema_reference(self) -> None:
        """
        Purpose: Verify RESPONSE_RULE references the JSON schema.
        Why this matters: Agent needs schema to produce valid structured output.
        Setup summary: Import constant; assert contains schema keyword.
        """
        from unique_web_search.services.search_engine.utils.grounding.bing.models import (
            RESPONSE_RULE,
        )

        assert isinstance(RESPONSE_RULE, str)
        assert "JSON Schema" in RESPONSE_RULE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
