"""Tests for ResponsesPlanningMiddleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses import Response, ResponseOutputMessage, ResponseOutputText

from unique_toolkit.agentic.loop_runner.middleware.planning.planning import (
    PlanningConfig,
    ResponsesPlanningMiddleware,
    _get_first_output_text,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessages,
    LanguageModelUserMessage,
)


def _make_middleware(
    *,
    loop_runner: AsyncMock | None = None,
    history_manager: MagicMock | None = None,
) -> tuple[ResponsesPlanningMiddleware, AsyncMock, AsyncMock]:
    """Create a ResponsesPlanningMiddleware with mocked dependencies."""
    openai_client = AsyncMock()
    runner = loop_runner or AsyncMock()
    middleware = ResponsesPlanningMiddleware(
        loop_runner=runner,
        config=PlanningConfig(),
        openai_client=openai_client,
        history_manager=history_manager,
    )
    return middleware, runner, openai_client


def _make_model_mock(name: str = "gpt-4o") -> MagicMock:
    model = MagicMock()
    model.name = name
    return model


def _make_response(output_text: str = '{"plan": "do stuff"}') -> MagicMock:
    """Create a mock Response with a single ResponseOutputMessage containing text."""
    text_content = MagicMock(spec=ResponseOutputText)
    text_content.type = "output_text"
    text_content.text = output_text

    message = MagicMock(spec=ResponseOutputMessage)
    message.content = [text_content]

    response = MagicMock(spec=Response)
    response.output = [message]
    return response


def _base_kwargs(**overrides):
    defaults = dict(
        iteration_index=0,
        streaming_handler=MagicMock(),
        messages=LanguageModelMessages([LanguageModelUserMessage(content="Hello")]),
        model=_make_model_mock(),
    )
    defaults.update(overrides)
    return defaults


# ============================================================================
# Tests for __call__
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__calls_loop_runner_with_plan_appended() -> None:
    """
    Purpose: Verify that a successful plan step appends the assistant message and calls the inner runner.
    Why this matters: Core happy-path behaviour of the middleware.
    Setup summary: Mock openai_client to return a plan, verify messages passed to inner runner.
    """
    middleware, runner, openai_client = _make_middleware()
    plan_response = _make_response('{"plan": "search the docs"}')
    openai_client.responses.create = AsyncMock(return_value=plan_response)

    kwargs = _base_kwargs()
    await middleware(**kwargs)

    runner.assert_awaited_once()
    call_kwargs = runner.call_args[1]
    last_msg = call_kwargs["messages"].root[-1]
    assert isinstance(last_msg, LanguageModelAssistantMessage)
    assert last_msg.content == '{"plan": "search the docs"}'


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__falls_back_when_plan_step_returns_none() -> None:
    """
    Purpose: Verify the middleware falls back to the inner runner when planning fails.
    Why this matters: Planning is optional; failures must not block the main loop.
    Setup summary: Mock _run_plan_step to return None, verify inner runner called with original messages.
    """
    middleware, runner, _ = _make_middleware()
    original_messages = LanguageModelMessages(
        [LanguageModelUserMessage(content="Hello")]
    )
    kwargs = _base_kwargs(messages=original_messages)

    with patch.object(
        middleware, "_run_plan_step", new_callable=AsyncMock, return_value=None
    ):
        await middleware(**kwargs)

    runner.assert_awaited_once()
    call_kwargs = runner.call_args[1]
    assert call_kwargs["messages"] is original_messages


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__adds_to_history_manager_when_present() -> None:
    """
    Purpose: Verify that the plan is added to the history manager when one is provided.
    Why this matters: History tracking is needed for multi-turn conversation context.
    Setup summary: Provide a mock history_manager, check add_assistant_message is called.
    """
    history_manager = MagicMock()
    middleware, runner, openai_client = _make_middleware(
        history_manager=history_manager
    )
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware(**_base_kwargs())

    history_manager.add_assistant_message.assert_called_once()
    msg = history_manager.add_assistant_message.call_args[0][0]
    assert isinstance(msg, LanguageModelAssistantMessage)


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__skips_history_manager_when_absent() -> None:
    """
    Purpose: Verify no error when history_manager is None.
    Why this matters: History manager is optional; middleware must not crash without it.
    Setup summary: Create middleware without history_manager, run successfully.
    """
    middleware, runner, openai_client = _make_middleware(history_manager=None)
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware(**_base_kwargs())

    runner.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__handles_string_messages() -> None:
    """
    Purpose: Verify that string messages are converted to a user + assistant message list.
    Why this matters: The messages kwarg can be a plain string in the Responses API.
    Setup summary: Pass a string as messages, verify the inner runner receives a list.
    """
    middleware, runner, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(
        return_value=_make_response('{"plan": "go"}')
    )

    kwargs = _base_kwargs(messages="What is the weather?")
    await middleware(**kwargs)

    call_kwargs = runner.call_args[1]
    messages = call_kwargs["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert isinstance(messages[0], LanguageModelUserMessage)
    assert messages[0].content == "What is the weather?"
    assert isinstance(messages[1], LanguageModelAssistantMessage)
    assert messages[1].content == '{"plan": "go"}'


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__handles_sequence_messages() -> None:
    """
    Purpose: Verify that a plain sequence of messages gets the plan appended.
    Why this matters: Messages can also be a Sequence[ResponseInputItemParam | ...].
    Setup summary: Pass a list of dicts as messages, verify plan is appended.
    """
    middleware, runner, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(
        return_value=_make_response('{"plan": "go"}')
    )

    input_messages = [{"role": "user", "content": "Hi"}]
    kwargs = _base_kwargs(messages=input_messages)
    await middleware(**kwargs)

    call_kwargs = runner.call_args[1]
    messages = call_kwargs["messages"]
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert isinstance(messages[-1], LanguageModelAssistantMessage)


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__passes_model_name_to_openai() -> None:
    """
    Purpose: Verify the correct model name is forwarded to the OpenAI client.
    Why this matters: Wrong model name would cause incorrect billing or capabilities.
    Setup summary: Set model.name, verify it is passed to openai_client.responses.create.
    """
    middleware, runner, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    model = _make_model_mock(name="o3-mini")
    await middleware(**_base_kwargs(model=model))

    create_call = openai_client.responses.create
    create_call.assert_awaited_once()
    assert create_call.call_args[1]["model"] == "o3-mini"


# ============================================================================
# Tests for _run_plan_step
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__returns_none_on_empty_output_text() -> None:
    """
    Purpose: Verify _run_plan_step returns None when the response has empty output_text.
    Why this matters: Empty plans should be treated as failures and trigger the fallback path.
    Setup summary: Mock response.output_text as empty string.
    """
    middleware, _, openai_client = _make_middleware()
    empty_response = _make_response(output_text="")
    openai_client.responses.create = AsyncMock(return_value=empty_response)

    result = await middleware._run_plan_step(
        openai_messages="test", model_name="gpt-4o"
    )

    assert result is None


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__returns_text_on_success() -> None:
    """
    Purpose: Verify _run_plan_step returns the output text string on success.
    Why this matters: The caller uses the returned text to build the assistant message.
    Setup summary: Mock a valid response, verify the text is returned.
    """
    middleware, _, openai_client = _make_middleware()
    plan_response = _make_response('{"plan": "search"}')
    openai_client.responses.create = AsyncMock(return_value=plan_response)

    result = await middleware._run_plan_step(
        openai_messages="test", model_name="gpt-4o"
    )

    assert result == '{"plan": "search"}'


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__returns_none_on_exception() -> None:
    """
    Purpose: Verify _run_plan_step returns None when the OpenAI call raises.
    Why this matters: The @failsafe_async decorator should catch exceptions and return None.
    Setup summary: Mock openai_client to raise, verify None returned.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(side_effect=RuntimeError("API down"))

    result = await middleware._run_plan_step(
        openai_messages="test", model_name="gpt-4o"
    )

    assert result is None


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__sends_json_schema_format() -> None:
    """
    Purpose: Verify the planning schema is sent as a JSON schema format parameter.
    Why this matters: Structured output requires the correct format specification.
    Setup summary: Inspect the `text` kwarg passed to openai_client.responses.create.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware._run_plan_step(openai_messages="test", model_name="gpt-4o")

    call_kwargs = openai_client.responses.create.call_args[1]
    text_param = call_kwargs["text"]
    assert "format" in text_param
    assert text_param["format"]["type"] == "json_schema"
    assert "schema" in text_param["format"]


# ============================================================================
# Tests for _get_first_output_text
# ============================================================================


@pytest.mark.ai
def test_get_first_output_text__picks_first_message_from_multiple_outputs() -> None:
    """
    Purpose: Verify that only the first viable message text is returned when
    the response contains multiple output items.
    Why this matters: The Responses API can return multiple outputs; we must
    use only the first text to avoid concatenating unrelated content.
    """
    text1 = MagicMock(spec=ResponseOutputText)
    text1.type = "output_text"
    text1.text = "first plan"

    text2 = MagicMock(spec=ResponseOutputText)
    text2.type = "output_text"
    text2.text = "second plan"

    msg1 = MagicMock(spec=ResponseOutputMessage)
    msg1.content = [text1]

    msg2 = MagicMock(spec=ResponseOutputMessage)
    msg2.content = [text2]

    response = MagicMock(spec=Response)
    response.output = [msg1, msg2]

    assert _get_first_output_text(response) == "first plan"


@pytest.mark.ai
def test_get_first_output_text__skips_non_message_outputs() -> None:
    """
    Purpose: Verify that non-message output items (e.g. tool calls) are skipped.
    Why this matters: The output list can contain tool calls and other item types.
    """
    tool_call = MagicMock()  # Not a ResponseOutputMessage

    text = MagicMock(spec=ResponseOutputText)
    text.type = "output_text"
    text.text = "the plan"

    msg = MagicMock(spec=ResponseOutputMessage)
    msg.content = [text]

    response = MagicMock(spec=Response)
    response.output = [tool_call, msg]

    assert _get_first_output_text(response) == "the plan"


@pytest.mark.ai
def test_get_first_output_text__returns_none_for_empty_output() -> None:
    """
    Purpose: Verify None is returned when the output list is empty.
    """
    response = MagicMock(spec=Response)
    response.output = []

    assert _get_first_output_text(response) is None
