import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from google.genai import types as genai_types
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.language_model.schemas import LanguageModelFunction

from unique_web_search.invocation_stats import (
    invocation_stats_scope,
    record_language_model_response,
    record_token_usage,
    record_vertex_response,
)
from unique_web_search.service import WebSearchTool


@pytest.mark.ai
def test_record_token_usage__skips_invalid_provider_usage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify malformed provider usage does not escape the stats collector.
    Why this matters: Optional billing metadata must not abort an in-flight Web Search.
    Setup summary: Record invalid token counts and assert the usage is skipped and logged.
    """
    with invocation_stats_scope() as invocation_stats:
        record_token_usage(
            model_name="provider-model",
            usage={"prompt_tokens": "not-a-token-count"},
            source="web_search.grounding.provider",
        )

    assert invocation_stats == []
    assert (
        "Unable to parse Web Search token usage for web_search.grounding.provider"
        in caplog.text
    )


@pytest.mark.ai
def test_record_vertex_response__normalizes_google_usage_metadata() -> None:
    """
    Purpose: Verify Vertex usage metadata is converted to toolkit token usage.
    Why this matters: Google uses different token field names than toolkit LLM responses.
        Using the real SDK type here (not a hand-rolled stand-in) means a future
        google-genai field rename breaks this test loudly instead of leaving
        `record_vertex_response` silently reporting `None` usage.
    Setup summary: Record a synthetic Vertex response and assert every supported token field.
    """
    response = SimpleNamespace(
        usage_metadata=genai_types.GenerateContentResponseUsageMetadata(
            prompt_token_count=11,
            candidates_token_count=7,
            total_token_count=20,
            thoughts_token_count=2,
            cached_content_token_count=3,
        )
    )

    with invocation_stats_scope() as invocation_stats:
        record_vertex_response(
            model_name="gemini-test",
            response=response,
            source="web_search.grounding.vertexai",
        )

    assert len(invocation_stats) == 1
    assert invocation_stats[0].model_name == "gemini-test"
    assert invocation_stats[0].source == "web_search.grounding.vertexai"
    assert invocation_stats[0].token_usage.prompt_tokens == 11
    assert invocation_stats[0].token_usage.completion_tokens == 7
    assert invocation_stats[0].token_usage.total_tokens == 20
    assert invocation_stats[0].token_usage.reasoning_tokens == 2
    assert invocation_stats[0].token_usage.cached_tokens == 3


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__isolates_invocation_stats__across_concurrent_calls(
    mocker: Any,
) -> None:
    """
    Purpose: Verify concurrent calls on one WebSearchTool receive only their own LLM usage.
    Why this matters: Tool instances may serve overlapping runs and must not mix billing data.
    Setup summary: Interleave two mocked runs, record distinct usage, and inspect both responses.
    """
    both_runs_started = asyncio.Event()
    started_runs = 0

    async def fake_run(
        self: WebSearchTool,
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
            source=f"web_search.test.{prompt_tokens}",
        )
        started_runs += 1
        if started_runs == 2:
            both_runs_started.set()
        await both_runs_started.wait()
        return ToolCallResponse(id=tool_call.id, name="WebSearch")

    mocker.patch.object(WebSearchTool, "_run", fake_run)
    tool = WebSearchTool.__new__(WebSearchTool)
    first_call = LanguageModelFunction(
        id="first",
        name="WebSearch",
        arguments={"prompt_tokens": 3},
    )
    second_call = LanguageModelFunction(
        id="second",
        name="WebSearch",
        arguments={"prompt_tokens": 9},
    )

    first, second = await asyncio.gather(tool.run(first_call), tool.run(second_call))

    assert [stat.source for stat in first.invocation_stats] == ["web_search.test.3"]
    assert first.invocation_stats[0].token_usage.prompt_tokens == 3
    assert [stat.source for stat in second.invocation_stats] == ["web_search.test.9"]
    assert second.invocation_stats[0].token_usage.prompt_tokens == 9
