import asyncio
from types import SimpleNamespace

import pytest
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_deep_research.invocation_stats import (
    invocation_stats_scope,
    record_invocation_stats,
    record_language_model_response,
)


@pytest.mark.ai
def test_record_language_model_response__uses_response_metadata__when_usage_metadata_missing() -> (
    None
):
    """
    Purpose: Verify OpenAI-compatible LangChain response metadata is accepted as a fallback.
    Why this matters: Provider adapters do not all populate AIMessage.usage_metadata.
    Setup summary: Record response_metadata.token_usage and assert normalized toolkit fields.
    """
    # Arrange
    response = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 13,
                "completion_tokens": 5,
                "total_tokens": 18,
            }
        }
    )

    # Act
    with invocation_stats_scope() as invocation_stats:
        record_language_model_response(
            model_name="gpt-test",
            response=response,
            source="deep_research.supervisor",
        )

    # Assert
    assert len(invocation_stats) == 1
    assert invocation_stats[0].token_usage.prompt_tokens == 13
    assert invocation_stats[0].token_usage.completion_tokens == 5
    assert invocation_stats[0].token_usage.total_tokens == 18


@pytest.mark.ai
@pytest.mark.asyncio
async def test_invocation_stats_scope__isolates_parallel_deep_research_runs() -> None:
    """
    Purpose: Verify overlapping Deep Research runs cannot mix their LLM usage records.
    Why this matters: LangGraph researchers execute concurrently and tool instances may overlap.
    Setup summary: Interleave two scopes, record distinct usage, and assert isolated results.
    """
    # Arrange
    both_runs_started = asyncio.Event()
    started_runs = 0

    async def collect_usage(prompt_tokens: int):
        nonlocal started_runs
        with invocation_stats_scope() as invocation_stats:
            started_runs += 1
            if started_runs == 2:
                both_runs_started.set()
            await both_runs_started.wait()
            record_language_model_response(
                model_name=f"model-{prompt_tokens}",
                response=SimpleNamespace(
                    usage_metadata={
                        "input_tokens": prompt_tokens,
                        "output_tokens": 1,
                        "total_tokens": prompt_tokens + 1,
                    }
                ),
                source=f"deep_research.test.{prompt_tokens}",
            )
        return invocation_stats

    # Act
    first, second = await asyncio.gather(collect_usage(3), collect_usage(9))

    # Assert
    assert [stat.source for stat in first] == ["deep_research.test.3"]
    assert first[0].token_usage.prompt_tokens == 3
    assert [stat.source for stat in second] == ["deep_research.test.9"]
    assert second[0].token_usage.prompt_tokens == 9


@pytest.mark.ai
def test_record_invocation_stats__merges_nested_dependency_usage__inside_scope() -> (
    None
):
    """
    Purpose: Verify LLM usage collected by nested web-search services reaches Deep Research.
    Why this matters: Custom Deep Research invokes search services without a WebSearch tool response.
    Setup summary: Merge one nested invocation into a run scope and assert it is retained unchanged.
    """
    # Arrange
    nested_invocation = LanguageModelInvocationStats.from_usage(
        model_name="gemini-test",
        token_usage=LanguageModelTokenUsage(
            prompt_tokens=8,
            completion_tokens=2,
            total_tokens=10,
        ),
        source="web_search.grounding.vertexai",
    )

    # Act
    with invocation_stats_scope() as invocation_stats:
        record_invocation_stats([nested_invocation])

    # Assert
    assert invocation_stats == [nested_invocation]
