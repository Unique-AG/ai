"""Recovery in ``UniqueAI._plan_or_execute`` when the provider rejects the prompt as too long (UN-27401)."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unique_toolkit.agentic.history_manager.context_overflow import (
    CONTEXT_OVERFLOW_TOKEN_BUDGET_FACTOR,
    WITHHELD_TOOL_RESULT_NOTICE,
)
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.language_model.schemas import LanguageModelTokenLimits
from unique_toolkit.language_model.settings import ModelFamily

if TYPE_CHECKING:
    from unique_orchestrator.unique_ai import UniqueAI

OVERFLOW = Exception("prompt is too long: 1012345 tokens > 1000000 maximum")


@pytest.fixture
def mock_unique_ai(monkeypatch: pytest.MonkeyPatch) -> UniqueAI:
    mock_service_module = MagicMock()
    mock_service_module.MessageStepLogger = MagicMock()
    monkeypatch.setitem(
        sys.modules,
        "unique_toolkit.agentic.message_log_manager.service",
        mock_service_module,
    )

    from unique_orchestrator.unique_ai import UniqueAI

    dummy_event = MagicMock()
    dummy_event.payload.assistant_message.id = "assist_1"
    dummy_event.payload.user_message.text = "query"
    dummy_event.payload.skill_choices = []
    dummy_event.company_id = "co-1"

    mock_config = MagicMock()
    mock_config.agent.prompt_config.user_metadata = []
    mock_config.agent.experimental.open_file_tool_config.enabled = False
    mock_config.agent.experimental.responses_api_config.use_responses_api = False
    mock_config.agent.experimental.use_responses_api = False

    ua = UniqueAI(
        logger=MagicMock(),
        event=dummy_event,
        config=mock_config,
        chat_service=MagicMock(),
        content_service=MagicMock(),
        debug_info_manager=MagicMock(),
        streaming_handler=MagicMock(),
        reference_manager=MagicMock(),
        thinking_manager=MagicMock(),
        tool_manager=MagicMock(),
        history_manager=MagicMock(),
        evaluation_manager=MagicMock(),
        postprocessor_manager=MagicMock(),
        message_step_logger=MagicMock(),
        mcp_servers=[],
        loop_iteration_runner=AsyncMock(),
    )
    ua._compose_message_plan_execution = AsyncMock(return_value=MagicMock())
    ua._record_loop_debug_params = MagicMock()
    return ua


async def _plan_or_execute(ua: UniqueAI) -> object:
    with patch("unique_orchestrator.unique_ai.resolve_other_options", return_value={}):
        return await ua._plan_or_execute()


def _configure_claude_preflight(ua: UniqueAI) -> AsyncMock:
    ua._config.space.language_model = LanguageModelInfo(
        name="litellm:claude-sonnet-5-5",
        family=ModelFamily.ANTHROPIC,
        version="claude-sonnet-5-5",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=769_230,
            token_limit_output=98_461,
        ),
    )
    ua._history_manager.last_token_count = 600_000
    ua._history_manager.effective_token_limit = 600_000
    counter = AsyncMock()
    ua._streaming_handler.count_tokens_async = counter
    return counter


@pytest.mark.ai
@pytest.mark.asyncio
async def test_preflight__accepts_provider_count_within_budget_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Near-limit local payloads are verified by the provider before generation.
    Why this matters: The local tokenizer can materially undercount Claude prompts.
    Setup summary: 600k local estimate, 930k provider count, 940k target -> run unchanged.
    """
    counter = _configure_claude_preflight(mock_unique_ai)
    counter.return_value = 930_000
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.return_value = response

    assert await _plan_or_execute(mock_unique_ai) is response

    counter.assert_awaited_once()
    mock_unique_ai._history_manager.tighten_token_budget.assert_not_called()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_preflight__skips_provider_below_local_trigger_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Avoid provider-count latency for ordinary payloads.
    Why this matters: The extra network request should only affect near-limit model calls.
    Setup summary: 500k local estimate below the 570k trigger -> generate directly.
    """
    counter = _configure_claude_preflight(mock_unique_ai)
    mock_unique_ai._history_manager.last_token_count = 500_000
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.return_value = response

    assert await _plan_or_execute(mock_unique_ai) is response

    counter.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_preflight__skips_non_anthropic_models_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Do not call the Anthropic token counter for non-Anthropic models.
    Why this matters: The proxy counter endpoint only accepts Anthropic-routed models.
    Setup summary: Near-limit OpenAI model -> generate directly without provider counting.
    """
    counter = _configure_claude_preflight(mock_unique_ai)
    mock_unique_ai._config.space.language_model = LanguageModelInfo(
        name="AZURE_GPT_4o_2024_1120",
        family=ModelFamily.OPENAI,
        version="2024-11-20",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=128_000,
            token_limit_output=16_384,
        ),
    )
    mock_unique_ai._history_manager.last_token_count = 120_000
    mock_unique_ai._history_manager.effective_token_limit = 120_000
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.return_value = response

    assert await _plan_or_execute(mock_unique_ai) is response

    counter.assert_not_awaited()


@pytest.mark.ai
@pytest.mark.asyncio
async def test_preflight__provider_counter_failure_falls_back_to_local_budget_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Provider-count availability must not become a new chat failure mode.
    Why this matters: Proxy or provider counter outages should preserve existing behavior.
    Setup summary: Near-limit payload, counter raises -> generate with the local reduced payload.
    """
    counter = _configure_claude_preflight(mock_unique_ai)
    counter.side_effect = Exception("counter unavailable")
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.return_value = response

    assert await _plan_or_execute(mock_unique_ai) is response

    counter.assert_awaited_once()
    assert mock_unique_ai._loop_iteration_runner.await_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_preflight__reduces_over_budget_payload_before_generation_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Provider-confirmed overflow reduces history and verifies the recomposed payload.
    Why this matters: The oversized model request must never be sent merely because local counting passed.
    Setup summary: 990k provider count then 900k after reduction -> one generation call.
    """
    counter = _configure_claude_preflight(mock_unique_ai)
    counter.side_effect = [990_000, 900_000]
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.return_value = response

    assert await _plan_or_execute(mock_unique_ai) is response

    mock_unique_ai._history_manager.tighten_token_budget.assert_called_once_with(0.9)
    mock_unique_ai._history_manager.withhold_latest_tool_call_results.assert_not_called()
    assert counter.await_count == 2
    assert mock_unique_ai._loop_iteration_runner.await_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_preflight__withholds_latest_batch_when_reduction_is_insufficient_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Persistent provider overflow falls back to withholding the latest tool batch.
    Why this matters: Parallel high-context tool calls must degrade into a sequential retry instruction.
    Setup summary: Counts remain over target after reduction, latest batch exists -> withhold and recount.
    """
    counter = _configure_claude_preflight(mock_unique_ai)
    counter.side_effect = [990_000, 970_000, 100_000]
    mock_unique_ai._history_manager.withhold_latest_tool_call_results.return_value = 2
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.return_value = response

    assert await _plan_or_execute(mock_unique_ai) is response

    mock_unique_ai._history_manager.withhold_latest_tool_call_results.assert_called_once_with(
        WITHHELD_TOOL_RESULT_NOTICE
    )
    assert counter.await_count == 3
    assert mock_unique_ai._loop_iteration_runner.await_count == 1


@pytest.mark.ai
@pytest.mark.asyncio
async def test_overflow__retries_with_tighter_budget_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: A first overflow tightens the token budget and retries with recomposed messages.
    Why this matters: Truncated tool results are preferred over losing them entirely.
    Setup summary: Runner fails once with overflow, then succeeds -> no results withheld.
    """
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.side_effect = [OVERFLOW, response]

    assert await _plan_or_execute(mock_unique_ai) is response

    mock_unique_ai._history_manager.tighten_token_budget.assert_called_once_with(
        CONTEXT_OVERFLOW_TOKEN_BUDGET_FACTOR
    )
    mock_unique_ai._history_manager.withhold_latest_tool_call_results.assert_not_called()
    assert mock_unique_ai._compose_message_plan_execution.await_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_repeated_overflow__withholds_latest_tool_results_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: A second overflow withholds the latest tool-call batch and retries once more.
    Why this matters: The turn completes and the model is told to call the tools sequentially.
    Setup summary: Runner overflows twice, then succeeds.
    """
    response = MagicMock()
    mock_unique_ai._loop_iteration_runner.side_effect = [OVERFLOW, OVERFLOW, response]
    mock_unique_ai._history_manager.withhold_latest_tool_call_results.return_value = 2

    assert await _plan_or_execute(mock_unique_ai) is response

    mock_unique_ai._history_manager.withhold_latest_tool_call_results.assert_called_once_with(
        WITHHELD_TOOL_RESULT_NOTICE
    )
    assert mock_unique_ai._compose_message_plan_execution.await_count == 3


@pytest.mark.ai
@pytest.mark.asyncio
async def test_repeated_overflow__reraises_when_nothing_to_withhold_AI(
    mock_unique_ai: UniqueAI,
) -> None:
    """
    Purpose: Without tool results to withhold, the overflow propagates.
    Why this matters: Retrying an unchanged payload would just fail again.
    Setup summary: Runner overflows twice, withhold returns 0 -> original error raised.
    """
    mock_unique_ai._loop_iteration_runner.side_effect = [OVERFLOW, OVERFLOW]
    mock_unique_ai._history_manager.withhold_latest_tool_call_results.return_value = 0

    with pytest.raises(Exception, match="prompt is too long"):
        await _plan_or_execute(mock_unique_ai)

    assert mock_unique_ai._loop_iteration_runner.await_count == 2


@pytest.mark.ai
@pytest.mark.asyncio
async def test_other_error__is_not_retried_AI(mock_unique_ai: UniqueAI) -> None:
    """
    Purpose: Errors other than context overflow propagate without a retry.
    Setup summary: Runner raises a rate-limit error -> raised, budget untouched.
    """
    mock_unique_ai._loop_iteration_runner.side_effect = Exception("Rate limit reached")

    with pytest.raises(Exception, match="Rate limit"):
        await _plan_or_execute(mock_unique_ai)

    mock_unique_ai._history_manager.tighten_token_budget.assert_not_called()
    assert mock_unique_ai._loop_iteration_runner.await_count == 1
