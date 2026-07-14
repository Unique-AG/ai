"""Tests for PlanningMiddleware (Chat Completions path)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unique_toolkit.agentic.loop_runner.middleware.planning.planning import (
    PlanningConfig,
    PlanningMiddleware,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelMessages,
    LanguageModelTokenUsage,
    LanguageModelUserMessage,
)


def _make_middleware(
    *,
    loop_runner: AsyncMock | None = None,
    history_manager: MagicMock | None = None,
    config: PlanningConfig | None = None,
) -> tuple[PlanningMiddleware, AsyncMock, AsyncMock]:
    llm_service = AsyncMock()
    runner = loop_runner or AsyncMock()
    middleware = PlanningMiddleware(
        loop_runner=runner,
        config=config or PlanningConfig(),
        llm_service=llm_service,
        history_manager=history_manager,
    )
    return middleware, runner, llm_service


def _make_model_mock(name: str = "gpt-4o") -> MagicMock:
    model = MagicMock()
    model.name = name
    return model


def _make_response(
    parsed: dict | None = None,
    *,
    usage: LanguageModelTokenUsage | None = None,
) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.parsed = (
        parsed if parsed is not None else {"plan": "do stuff"}
    )
    response.usage = usage
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


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__calls_loop_runner_with_plan_appended() -> None:
    middleware, runner, llm_service = _make_middleware()
    llm_service.complete_async = AsyncMock(
        return_value=_make_response({"plan": "search the docs"})
    )

    await middleware(**_base_kwargs())

    runner.assert_awaited_once()
    call_kwargs = runner.call_args[1]
    last_msg = call_kwargs["messages"].root[-1]
    assert isinstance(last_msg, LanguageModelAssistantMessage)


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__falls_back_when_plan_step_returns_none() -> None:
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
    assert runner.call_args[1]["messages"] is original_messages


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__adds_to_history_manager_when_present() -> None:
    history_manager = MagicMock()
    middleware, _, llm_service = _make_middleware(history_manager=history_manager)
    llm_service.complete_async = AsyncMock(return_value=_make_response())

    await middleware(**_base_kwargs())

    history_manager.add_assistant_message.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__captures_invocation_stats_on_usage() -> None:
    """The planning call is a real, separate LLM call the main loop never
    sees — its usage must be captured under source="planning" so it isn't
    silently dropped from the turn's total."""
    middleware, _, llm_service = _make_middleware()
    usage = LanguageModelTokenUsage(
        completion_tokens=5, prompt_tokens=10, total_tokens=15
    )
    llm_service.complete_async = AsyncMock(return_value=_make_response(usage=usage))

    model = _make_model_mock(name="gpt-4o-mini")
    await middleware(**_base_kwargs(model=model))

    stats = middleware.get_invocation_stats()
    assert len(stats) == 1
    assert stats[0].model_info == "gpt-4o-mini"
    assert stats[0].source == "planning"
    assert stats[0].token_usage == usage


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__no_usage_on_response__no_stats_captured() -> None:
    middleware, _, llm_service = _make_middleware()
    llm_service.complete_async = AsyncMock(return_value=_make_response(usage=None))

    await middleware(**_base_kwargs())

    assert middleware.get_invocation_stats() == []


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__get_invocation_stats_drains_between_calls() -> None:
    """get_invocation_stats() must return-and-clear so repeated iterations
    (the middleware instance is reused across loop iterations) don't
    double-count a prior iteration's planning call."""
    middleware, _, llm_service = _make_middleware()
    usage = LanguageModelTokenUsage(
        completion_tokens=1, prompt_tokens=1, total_tokens=2
    )
    llm_service.complete_async = AsyncMock(return_value=_make_response(usage=usage))

    await middleware(**_base_kwargs())
    first_drain = middleware.get_invocation_stats()
    second_drain = middleware.get_invocation_stats()

    assert len(first_drain) == 1
    assert second_drain == []


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__plan_step_failure__no_stats_captured() -> None:
    """When the plan step raises and is swallowed by @failsafe_async, no
    usage was ever obtained, so nothing is captured."""
    middleware, runner, llm_service = _make_middleware()
    llm_service.complete_async = AsyncMock(side_effect=RuntimeError("boom"))

    await middleware(**_base_kwargs())

    runner.assert_awaited_once()
    assert middleware.get_invocation_stats() == []


@pytest.mark.asyncio
@pytest.mark.ai
async def test_planning__parse_failure_after_usage__stats_still_captured() -> None:
    """Tokens are spent even if the model's output fails to parse — the
    usage must still be recorded even though the plan step itself falls
    back to None."""
    middleware, runner, llm_service = _make_middleware()
    usage = LanguageModelTokenUsage(
        completion_tokens=1, prompt_tokens=1, total_tokens=2
    )
    llm_service.complete_async = AsyncMock(
        return_value=_make_response(parsed=None, usage=usage)
    )

    await middleware(**_base_kwargs())

    runner.assert_awaited_once()
    stats = middleware.get_invocation_stats()
    assert len(stats) == 1
    assert stats[0].token_usage == usage
