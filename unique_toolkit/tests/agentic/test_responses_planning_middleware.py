"""Tests for ResponsesPlanningMiddleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai.types.responses import Response, ResponseFunctionToolCall

from unique_toolkit.agentic.loop_runner.middleware.planning.planning import (
    _PLAN_TOOL_NAME,
    PlanningConfig,
    ResponsesPlanningMiddleware,
    _get_first_tool_call_arguments,
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
    config: PlanningConfig | None = None,
) -> tuple[ResponsesPlanningMiddleware, AsyncMock, AsyncMock]:
    """Create a ResponsesPlanningMiddleware with mocked dependencies."""
    openai_client = AsyncMock()
    runner = loop_runner or AsyncMock()
    middleware = ResponsesPlanningMiddleware(
        loop_runner=runner,
        config=config or PlanningConfig(),
        openai_client=openai_client,
        history_manager=history_manager,
    )
    return middleware, runner, openai_client


def _make_model_mock(name: str = "gpt-4o") -> MagicMock:
    model = MagicMock()
    model.name = name
    return model


def _make_tool_call(arguments: str = '{"plan": "do stuff"}') -> MagicMock:
    call = MagicMock(spec=ResponseFunctionToolCall)
    call.arguments = arguments
    call.name = _PLAN_TOOL_NAME
    return call


def _make_response(arguments: str = '{"plan": "do stuff"}') -> MagicMock:
    """Create a mock Response whose output contains a single forced tool call."""
    response = MagicMock(spec=Response)
    response.output = [_make_tool_call(arguments)]
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


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__forwards_whitelisted_options() -> None:
    """
    Purpose: Whitelisted Responses options (e.g. ``reasoning``, ``temperature``)
    present on the loop-runner kwargs should flow into the plan call.
    Why this matters: Reasoning models and temperature tuning must apply to the
    planning step just like the main loop.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    reasoning = {"effort": "high"}
    await middleware(**_base_kwargs(reasoning=reasoning, temperature=0.1, top_p=0.5))

    call_kwargs = openai_client.responses.create.call_args[1]
    assert call_kwargs["reasoning"] == reasoning
    assert call_kwargs["temperature"] == 0.1
    assert call_kwargs["top_p"] == 0.5


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__does_not_forward_non_whitelisted_options() -> None:
    """
    Purpose: Loop-runner kwargs that conflict with the forced-tool-call setup
    (``tool_choices``, ``text``) must not leak into ``responses.create``.
    (``tools`` is handled separately — see the tool-passthrough tests.)
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware(
        **_base_kwargs(
            tool_choices=[{"type": "function", "name": "other"}],
            text={"format": {"type": "text"}},
        )
    )

    call_kwargs = openai_client.responses.create.call_args[1]
    assert call_kwargs["tool_choice"] == {
        "type": "function",
        "name": _PLAN_TOOL_NAME,
    }
    assert "text" not in call_kwargs
    assert "tool_choices" not in call_kwargs


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__forwards_loop_runner_tools() -> None:
    """
    Purpose: The loop runner's ``tools`` are passed alongside the forced
    ``plan`` tool so the model can reason about what it will eventually call.
    Why this matters: The planning prompt explicitly asks the model to name
    the next tool to invoke; it needs the tool catalogue in context.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    existing_tool: dict = {
        "type": "function",
        "name": "search_docs",
        "description": "Search the docs.",
        "parameters": {"type": "object", "properties": {}},
        "strict": False,
    }
    await middleware(**_base_kwargs(tools=[existing_tool]))

    call_kwargs = openai_client.responses.create.call_args[1]
    names = [t["name"] for t in call_kwargs["tools"]]
    assert names[0] == _PLAN_TOOL_NAME
    assert "search_docs" in names
    assert call_kwargs["tool_choice"] == {
        "type": "function",
        "name": _PLAN_TOOL_NAME,
    }


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__converts_tool_description_objects() -> None:
    """
    Purpose: ``LanguageModelToolDescription`` instances in ``tools`` are
    converted to the Responses-API ``FunctionToolParam`` shape before being
    sent.
    """
    from pydantic import BaseModel

    from unique_toolkit.language_model.schemas import LanguageModelToolDescription

    class _Params(BaseModel):
        query: str

    tool_desc = LanguageModelToolDescription(
        name="search_docs",
        description="Search the docs.",
        parameters=_Params,
    )

    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware(**_base_kwargs(tools=[tool_desc]))

    call_kwargs = openai_client.responses.create.call_args[1]
    names = [t["name"] for t in call_kwargs["tools"]]
    assert names == [_PLAN_TOOL_NAME, "search_docs"]
    search_tool = call_kwargs["tools"][1]
    assert search_tool["type"] == "function"
    assert isinstance(search_tool["parameters"], dict)


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__drops_duplicate_plan_named_tool() -> None:
    """
    Purpose: If a loop-runner tool happens to be named ``plan``, it is dropped
    in favor of the middleware's forced planning tool.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    conflicting: dict = {
        "type": "function",
        "name": _PLAN_TOOL_NAME,
        "description": "impostor",
        "parameters": {"type": "object", "properties": {}},
        "strict": False,
    }
    await middleware(**_base_kwargs(tools=[conflicting]))

    tools = openai_client.responses.create.call_args[1]["tools"]
    plan_tools = [t for t in tools if t["name"] == _PLAN_TOOL_NAME]
    assert len(plan_tools) == 1
    assert plan_tools[0]["description"] != "impostor"


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__respects_ignored_options_for_whitelisted() -> None:
    """
    Purpose: Options named in ``config.ignored_options`` are dropped even if
    they are on the whitelist.
    """
    config = PlanningConfig(ignored_options=["reasoning", "temperature"])
    middleware, _, openai_client = _make_middleware(config=config)
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware(
        **_base_kwargs(reasoning={"effort": "high"}, temperature=0.2, top_p=0.9)
    )

    call_kwargs = openai_client.responses.create.call_args[1]
    assert "reasoning" not in call_kwargs
    assert "temperature" not in call_kwargs
    assert call_kwargs["top_p"] == 0.9


@pytest.mark.asyncio
@pytest.mark.ai
async def test_responses_planning__forwards_and_filters_other_options() -> None:
    """
    Purpose: Keys from the ``other_options`` dict are forwarded, minus any that
    appear in ``ignored_options``.
    Why this matters: ``other_options`` is the escape hatch for options not in
    the whitelist; ``ignored_options`` must still gate it.
    """
    config = PlanningConfig(ignored_options=["parallel_tool_calls", "store"])
    middleware, _, openai_client = _make_middleware(config=config)
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware(**_base_kwargs(other_options={"user": "u-1", "store": True}))

    call_kwargs = openai_client.responses.create.call_args[1]
    assert call_kwargs["user"] == "u-1"
    assert "store" not in call_kwargs


# ============================================================================
# Tests for _run_plan_step
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__returns_none_on_empty_arguments() -> None:
    """
    Purpose: Verify _run_plan_step returns None when the tool call has empty arguments.
    Why this matters: Empty plans should be treated as failures and trigger the fallback path.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response(""))

    result = await middleware._run_plan_step(
        openai_messages="test", model_name="gpt-4o", tools=[], forwarded_options={}
    )

    assert result is None


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__returns_arguments_on_success() -> None:
    """
    Purpose: Verify _run_plan_step returns the tool call arguments on success.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(
        return_value=_make_response('{"plan": "search"}')
    )

    result = await middleware._run_plan_step(
        openai_messages="test", model_name="gpt-4o", tools=[], forwarded_options={}
    )

    assert result == '{"plan": "search"}'


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__returns_none_on_exception() -> None:
    """
    Purpose: Verify _run_plan_step returns None when the OpenAI call raises.
    Why this matters: The @failsafe_async decorator should catch exceptions and return None.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(side_effect=RuntimeError("API down"))

    result = await middleware._run_plan_step(
        openai_messages="test", model_name="gpt-4o", tools=[], forwarded_options={}
    )

    assert result is None


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__sends_forced_tool_call() -> None:
    """
    Purpose: The plan step must issue a forced function tool call carrying the
    planning JSON schema.
    Why this matters: This is the core fix for the duplicate-output issue the
    Responses API exhibits with ``text.format=json_schema``.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    prepared_tools = middleware._build_tools({})

    await middleware._run_plan_step(
        openai_messages="test",
        model_name="gpt-4o",
        tools=prepared_tools,
        forwarded_options={},
    )

    call_kwargs = openai_client.responses.create.call_args[1]
    assert "text" not in call_kwargs
    assert call_kwargs["tool_choice"] == {
        "type": "function",
        "name": _PLAN_TOOL_NAME,
    }
    tools = call_kwargs["tools"]
    assert len(tools) == 1
    assert tools[0]["type"] == "function"
    assert tools[0]["name"] == _PLAN_TOOL_NAME
    assert isinstance(tools[0]["parameters"], dict)


@pytest.mark.asyncio
@pytest.mark.ai
async def test_run_plan_step__splats_forwarded_options() -> None:
    """
    Purpose: ``forwarded_options`` are spread as kwargs onto ``responses.create``.
    """
    middleware, _, openai_client = _make_middleware()
    openai_client.responses.create = AsyncMock(return_value=_make_response())

    await middleware._run_plan_step(
        openai_messages="test",
        model_name="gpt-4o",
        tools=[],
        forwarded_options={"reasoning": {"effort": "low"}, "temperature": 0.3},
    )

    call_kwargs = openai_client.responses.create.call_args[1]
    assert call_kwargs["reasoning"] == {"effort": "low"}
    assert call_kwargs["temperature"] == 0.3


# ============================================================================
# Tests for _get_first_tool_call_arguments
# ============================================================================


@pytest.mark.ai
def test_get_first_tool_call_arguments__picks_first_call_from_multiple() -> None:
    """
    Purpose: When multiple tool-call items are returned, only the first one's
    arguments are used.
    Why this matters: Avoids concatenating / confusing duplicate plans.
    """
    response = MagicMock(spec=Response)
    response.output = [_make_tool_call("first plan"), _make_tool_call("second plan")]

    assert _get_first_tool_call_arguments(response) == "first plan"


@pytest.mark.ai
def test_get_first_tool_call_arguments__skips_non_tool_call_outputs() -> None:
    """
    Purpose: Non-tool-call output items (e.g. plain messages) must be skipped.
    """
    other = MagicMock()  # not a ResponseFunctionToolCall

    response = MagicMock(spec=Response)
    response.output = [other, _make_tool_call("the plan")]

    assert _get_first_tool_call_arguments(response) == "the plan"


@pytest.mark.ai
def test_get_first_tool_call_arguments__returns_none_for_empty_output() -> None:
    """
    Purpose: Verify None is returned when the output list is empty.
    """
    response = MagicMock(spec=Response)
    response.output = []

    assert _get_first_tool_call_arguments(response) is None


@pytest.mark.ai
def test_get_first_tool_call_arguments__returns_none_for_empty_arguments() -> None:
    """
    Purpose: A tool call with empty ``arguments`` yields None.
    """
    call = _make_tool_call("")
    response = MagicMock(spec=Response)
    response.output = [call]

    assert _get_first_tool_call_arguments(response) is None
