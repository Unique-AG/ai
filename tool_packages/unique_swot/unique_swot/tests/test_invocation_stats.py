import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_swot.invocation_stats import (
    invocation_stats_scope,
    record_language_model_response,
    record_token_usage,
)
from unique_swot.service import SwotAnalysisTool
from unique_swot.utils import generate_structured_output


class DummyOutput(BaseModel):
    value: str


@pytest.mark.ai
def test_record_token_usage__skips_invalid_provider_usage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify malformed provider usage does not escape the stats collector.
    Why this matters: Optional billing metadata must not abort an in-flight SWOT run.
    Setup summary: Record invalid token counts and assert the usage is skipped and logged.
    """
    with invocation_stats_scope() as invocation_stats:
        record_token_usage(
            model_name="provider-model",
            usage={"prompt_tokens": "not-a-token-count"},
            source="swot.generation.plan",
        )

    assert invocation_stats == []
    assert "Unable to parse SWOT token usage for swot.generation.plan" in caplog.text


@pytest.mark.ai
def test_record_token_usage__is_noop__when_no_scope_is_active() -> None:
    """
    Purpose: Verify recording outside a run scope does not raise or leak state.
    Why this matters: Nested SWOT helpers may run in tests or scripts without a tool run.
    Setup summary: Call record helpers with no active scope and assert they return.
    """
    record_token_usage(
        model_name="provider-model",
        usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        source="swot.test",
    )
    record_language_model_response(
        model_name="provider-model",
        response=SimpleNamespace(usage={"prompt_tokens": 1}),
        source="swot.test",
    )


@pytest.mark.ai
@pytest.mark.asyncio
async def test_generate_structured_output__records_usage__when_complete_succeeds() -> (
    None
):
    """
    Purpose: Verify the shared SWOT LLM helper records toolkit usage under the given source.
    Why this matters: Almost every SWOT call site goes through this helper; missing
        recording here would leave debug_info["llm_invocations"] empty.
    Setup summary: Complete once with usage, then assert the scoped stats match.
    """
    message = Mock(parsed={"value": "ok"})
    response = Mock(
        choices=[Mock(message=message)],
        usage={"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    )
    llm_service = Mock()
    llm_service.complete_async = AsyncMock(return_value=response)

    with invocation_stats_scope() as invocation_stats:
        result = await generate_structured_output(
            user_message="hi",
            system_prompt="sys",
            llm=SimpleNamespace(name="dummy-model"),
            output_model=DummyOutput,
            llm_service=llm_service,
            source="swot.generation.plan",
        )

    assert result is not None
    assert result.value == "ok"
    assert len(invocation_stats) == 1
    assert invocation_stats[0].source == "swot.generation.plan"
    assert invocation_stats[0].token_usage.prompt_tokens == 5
    assert invocation_stats[0].token_usage.completion_tokens == 2
    assert invocation_stats[0].token_usage.total_tokens == 7


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__isolates_invocation_stats__across_concurrent_calls(
    mocker: Any,
) -> None:
    """
    Purpose: Verify concurrent calls on one SwotAnalysisTool receive only their own LLM usage.
    Why this matters: Tool instances may serve overlapping runs and must not mix billing data.
    Setup summary: Interleave two mocked runs, record distinct usage, and inspect both responses.
    """
    both_runs_started = asyncio.Event()
    started_runs = 0

    async def fake_run(
        self: SwotAnalysisTool,
        tool_call: LanguageModelFunction,
    ) -> ToolCallResponse:
        del self
        nonlocal started_runs
        prompt_tokens = int(tool_call.arguments["prompt_tokens"])  # type: ignore[index]
        record_language_model_response(
            model_name=f"model-{prompt_tokens}",
            response=SimpleNamespace(
                usage={
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 1,
                    "total_tokens": prompt_tokens + 1,
                }
            ),
            source=f"swot.test.{prompt_tokens}",
        )
        started_runs += 1
        if started_runs == 2:
            both_runs_started.set()
        await both_runs_started.wait()
        return ToolCallResponse(id=tool_call.id, name="SwotAnalysis")

    mocker.patch.object(SwotAnalysisTool, "_run", fake_run)
    tool = SwotAnalysisTool.__new__(SwotAnalysisTool)
    first_call = LanguageModelFunction(
        id="first",
        name="SwotAnalysis",
        arguments={"prompt_tokens": 3},
    )
    second_call = LanguageModelFunction(
        id="second",
        name="SwotAnalysis",
        arguments={"prompt_tokens": 9},
    )

    first, second = await asyncio.gather(tool.run(first_call), tool.run(second_call))

    assert [stat.source for stat in first.invocation_stats] == ["swot.test.3"]
    assert first.invocation_stats[0].token_usage.prompt_tokens == 3
    assert [stat.source for stat in second.invocation_stats] == ["swot.test.9"]
    assert second.invocation_stats[0].token_usage.prompt_tokens == 9


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__preserves_invocation_stats__when_run_raises() -> None:
    """
    Purpose: Verify run() attaches already-collected invocation stats when _run() raises.
    Why this matters: SafeTaskExecutor builds a fresh stats-less error response one
        level up, so tokens spent before an unexpected failure would otherwise vanish.
    Setup summary: Mock _run() to record usage then raise, and assert run()'s error
        response still carries the stats.
    """

    async def _run_records_usage_then_fails(*_args: Any, **_kwargs: Any) -> None:
        record_language_model_response(
            model_name="gpt-test",
            response=SimpleNamespace(
                usage={
                    "prompt_tokens": 9,
                    "completion_tokens": 1,
                    "total_tokens": 10,
                }
            ),
            source="swot.summarization",
        )
        raise Exception("boom after summarization")

    tool = SwotAnalysisTool.__new__(SwotAnalysisTool)
    tool._run = _run_records_usage_then_fails  # type: ignore[method-assign]
    tool_call = Mock(spec=LanguageModelFunction)
    tool_call.id = "tool_call_123"

    result = await tool.run(tool_call)

    assert result.error_message == "boom after summarization"
    assert len(result.invocation_stats) == 1
    assert result.invocation_stats[0].source == "swot.summarization"
    assert result.invocation_stats[0].token_usage.prompt_tokens == 9
