import asyncio
from typing import Any

import pytest
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelTokenUsage,
)

from unique_internal_search.invocation_stats import record_invocation_stats
from unique_internal_search.service import InternalSearchTool


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__isolates_invocation_stats__across_concurrent_calls(
    mocker: Any,
) -> None:
    """
    Purpose: Verify concurrent calls on one InternalSearchTool receive only their own usage.
    Why this matters: Shared tool instances must not mix LLM billing data between responses.
    Setup summary: Interleave two mocked runs, record distinct usage, and inspect both responses.
    """
    both_runs_started = asyncio.Event()
    started_runs = 0

    async def fake_run(
        self: InternalSearchTool,
        tool_call: LanguageModelFunction,
    ) -> ToolCallResponse:
        del self
        nonlocal started_runs
        prompt_tokens = int(tool_call.arguments["prompt_tokens"])  # type: ignore[index]
        record_invocation_stats(
            [
                LanguageModelInvocationStats.from_usage(
                    model_name=f"model-{prompt_tokens}",
                    token_usage=LanguageModelTokenUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=1,
                        total_tokens=prompt_tokens + 1,
                    ),
                    source=f"internal_search.test.{prompt_tokens}",
                )
            ]
        )
        started_runs += 1
        if started_runs == 2:
            both_runs_started.set()
        await both_runs_started.wait()
        return ToolCallResponse(id=tool_call.id, name="InternalSearch")

    mocker.patch.object(InternalSearchTool, "_run", fake_run)
    tool = InternalSearchTool.__new__(InternalSearchTool)
    first_call = LanguageModelFunction(
        id="first",
        name="InternalSearch",
        arguments={"prompt_tokens": 3},
    )
    second_call = LanguageModelFunction(
        id="second",
        name="InternalSearch",
        arguments={"prompt_tokens": 9},
    )

    first, second = await asyncio.gather(tool.run(first_call), tool.run(second_call))

    assert [stat.source for stat in first.invocation_stats] == [
        "internal_search.test.3"
    ]
    assert first.invocation_stats[0].token_usage.prompt_tokens == 3
    assert [stat.source for stat in second.invocation_stats] == [
        "internal_search.test.9"
    ]
    assert second.invocation_stats[0].token_usage.prompt_tokens == 9
