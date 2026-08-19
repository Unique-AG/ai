import asyncio
import warnings
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.invocation_stats import (
    InvocationStatsCollector,
    LanguageModelInvocationStats,
)
from unique_toolkit.language_model.model_costs import MODEL_COSTS_FILE_ENV
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage


class TestLanguageModelInvocationStatsFromUsage:
    """`from_usage` is the single constructor for per-invocation stats."""

    @pytest.mark.ai
    def test_from_usage__builds_stats(self) -> None:
        usage = LanguageModelTokenUsage(
            completion_tokens=10, prompt_tokens=20, total_tokens=30
        )

        stats = LanguageModelInvocationStats.from_usage(
            "gpt-4-test", usage, source="main_loop"
        )

        assert stats.model_name == "gpt-4-test"
        assert stats.token_usage == usage
        assert stats.source == "main_loop"
        assert stats.cost_usd is None

    @pytest.mark.ai
    def test_from_usage__calculates_cost_from_configured_catalog(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Purpose: Verify invocation construction attaches its calculated USD cost.
        Why this matters: Every debug-info capture site uses this shared constructor.
        Setup summary: Configure a price sheet, build stats, and assert the cost.
        """
        cost_file = tmp_path / "costs.yaml"
        cost_file.write_text(
            """
costSchemaVersion: 1
models:
  gpt-4-test:
    input: 2
    completion: 8
""",
            encoding="utf-8",
        )
        monkeypatch.setenv(MODEL_COSTS_FILE_ENV, str(cost_file))
        usage = LanguageModelTokenUsage(prompt_tokens=1_000, completion_tokens=250)

        stats = LanguageModelInvocationStats.from_usage(
            "gpt-4-test", usage, source="main_loop"
        )

        assert stats.cost_usd == pytest.approx(0.004)

    @pytest.mark.ai
    def test_from_usage__source_required(self) -> None:
        usage = LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=2, total_tokens=3
        )

        with pytest.raises(TypeError):
            LanguageModelInvocationStats.from_usage("gpt-4-test", usage)  # type: ignore[call-arg]


class TestLanguageModelInvocationStatsSerialization:
    @pytest.mark.ai
    def test_model_dump_by_alias__camel_case_shape(self) -> None:
        stats = LanguageModelInvocationStats(
            model_name="gpt-4-test",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="main_loop",
        )

        dumped = stats.model_dump(by_alias=True)

        assert dumped == {
            "modelName": "gpt-4-test",
            "tokenUsage": {
                "completionTokens": 10,
                "promptTokens": 20,
                "totalTokens": 30,
                "reasoningTokens": None,
                "cachedTokens": None,
                "cacheWriteTokens": None,
            },
            "source": "main_loop",
            "costUsd": None,
        }


class TestLanguageModelInvocationStatsModelName:
    @pytest.mark.ai
    def test_model_name__accepts_language_model_name_enum__dumps_as_plain_string(
        self,
    ) -> None:
        stats = LanguageModelInvocationStats(
            model_name=LanguageModelName.AZURE_GPT_4o_2024_1120,
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert stats.model_name == LanguageModelName.AZURE_GPT_4o_2024_1120

        dumped = stats.model_dump(by_alias=True)
        assert dumped["modelName"] == LanguageModelName.AZURE_GPT_4o_2024_1120.value
        assert isinstance(dumped["modelName"], str)

    @pytest.mark.ai
    def test_model_name__accepts_arbitrary_string(self) -> None:
        stats = LanguageModelInvocationStats(
            model_name="some-custom-model-id",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert stats.model_name == "some-custom-model-id"
        assert stats.model_dump(by_alias=True)["modelName"] == "some-custom-model-id"

    @pytest.mark.ai
    def test_model_name__string_matching_known_name__normalized_to_enum(self) -> None:
        """Capture sites pass `.name` strings; a string that matches a
        `LanguageModelName` value must canonicalize to the enum so the same
        model never appears as both enum and str across entries."""
        stats = LanguageModelInvocationStats(
            model_name=LanguageModelName.AZURE_GPT_4o_2024_1120.value,
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert isinstance(stats.model_name, LanguageModelName)
        assert stats.model_name is LanguageModelName.AZURE_GPT_4o_2024_1120

    @pytest.mark.ai
    def test_model_name__string_is_stripped(self) -> None:
        stats = LanguageModelInvocationStats(
            model_name="  some-custom-model-id  ",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert stats.model_name == "some-custom-model-id"

    @pytest.mark.ai
    def test_model_name__empty_string__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_name="   ",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
                source="main_loop",
            )


class TestLanguageModelInvocationStatsSource:
    @pytest.mark.ai
    def test_source__missing__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_name="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
            )  # type: ignore[call-arg]

    @pytest.mark.ai
    def test_source__empty_string__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_name="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
                source="",
            )

    @pytest.mark.ai
    def test_source__whitespace_only__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_name="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
                source="   ",
            )

    @pytest.mark.ai
    def test_source__is_stripped(self) -> None:
        stats = LanguageModelInvocationStats(
            model_name="gpt-4-test",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="  main_loop  ",
        )

        assert stats.source == "main_loop"


class TestLanguageModelInvocationStatsNoProtectedNamespaceWarning:
    @pytest.mark.ai
    def test_construction__emits_no_protected_namespace_warning(self) -> None:
        """`model_name` starts with `model_` which pydantic normally flags as
        a protected-namespace clash; `protected_namespaces=()` on the shared
        model_config must silence that warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            LanguageModelInvocationStats(
                model_name="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
                source="main_loop",
            )

        protected_namespace_warnings = [
            warning
            for warning in caught
            if "protected namespace" in str(warning.message)
        ]
        assert protected_namespace_warnings == []


def _usage(prompt_tokens: int) -> dict[str, int]:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": 1,
        "total_tokens": prompt_tokens + 1,
    }


class TestInvocationStatsCollector:
    """Run-scoped ContextVar collector shared by tool packages."""

    @pytest.mark.ai
    def test_record_token_usage__appends_stats__when_scope_is_active(self) -> None:
        """
        Purpose: Verify valid provider usage is stored on the active run.
        Why this matters: Tool packages record billing metadata through this collector.
        Setup summary: Record one usage payload and assert the stored fields.
        """
        collector = InvocationStatsCollector("web_search")

        with collector.scope() as invocation_stats:
            collector.record_token_usage(
                model_name="gpt-test",
                usage=_usage(5),
                source="web_search.grounding.provider",
            )

        assert len(invocation_stats) == 1
        assert invocation_stats[0].model_name == "gpt-test"
        assert invocation_stats[0].source == "web_search.grounding.provider"
        assert invocation_stats[0].token_usage.prompt_tokens == 5
        assert invocation_stats[0].token_usage.completion_tokens == 1
        assert invocation_stats[0].token_usage.total_tokens == 6

    @pytest.mark.ai
    def test_record_token_usage__is_noop__when_no_scope_is_active(self) -> None:
        """
        Purpose: Verify recording outside a run scope does not raise or leak state.
        Why this matters: Nested helpers may run in tests or scripts without a tool run.
        Setup summary: Call record helpers with no active scope and assert they return.
        """
        collector = InvocationStatsCollector("web_search")

        collector.record_token_usage(
            model_name="gpt-test",
            usage=_usage(1),
            source="web_search.test",
        )
        collector.record_language_model_response(
            model_name="gpt-test",
            response=SimpleNamespace(usage=_usage(1)),
            source="web_search.test",
        )
        collector.record_invocation_stats(
            [
                LanguageModelInvocationStats.from_usage(
                    model_name="gpt-test",
                    token_usage=LanguageModelTokenUsage(
                        prompt_tokens=1, completion_tokens=1, total_tokens=2
                    ),
                    source="web_search.test",
                )
            ]
        )

    @pytest.mark.ai
    def test_record_token_usage__skips_invalid_provider_usage(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Purpose: Verify malformed provider usage does not escape the stats collector.
        Why this matters: Optional billing metadata must not abort an in-flight tool run.
        Setup summary: Record invalid token counts and assert the usage is skipped and logged.
        """
        collector = InvocationStatsCollector("web_search")

        with collector.scope() as invocation_stats:
            collector.record_token_usage(
                model_name="provider-model",
                usage={"prompt_tokens": "not-a-token-count"},
                source="web_search.grounding.provider",
            )

        assert invocation_stats == []
        assert (
            "Unable to parse web_search token usage for web_search.grounding.provider"
            in caplog.text
        )

    @pytest.mark.ai
    def test_record_token_usage__skips_from_usage_failures(
        self,
        caplog: pytest.LogCaptureFixture,
        mocker: Any,
    ) -> None:
        """
        Purpose: Verify exceptions from stats construction are swallowed, not only parse errors.
        Why this matters: The original copies drifted — some left from_usage() uncaught.
        Setup summary: Make from_usage raise and assert the run continues with empty stats.
        """
        collector = InvocationStatsCollector("deep_research")
        mocker.patch(
            "unique_toolkit.language_model.invocation_stats."
            "LanguageModelInvocationStats.from_usage",
            side_effect=RuntimeError("cost lookup failed"),
        )

        with collector.scope() as invocation_stats:
            collector.record_token_usage(
                model_name="gpt-test",
                usage=_usage(3),
                source="deep_research.supervisor",
            )

        assert invocation_stats == []
        assert (
            "Unable to parse deep_research token usage for deep_research.supervisor"
            in caplog.text
        )

    @pytest.mark.ai
    def test_record_invocation_stats__merges_nested_dependency_usage__inside_scope(
        self,
    ) -> None:
        """
        Purpose: Verify already-built stats from nested dependencies reach the active run.
        Why this matters: Deep Research merges Web Search usage without a tool response.
        Setup summary: Merge one nested invocation into a run scope and assert it is retained.
        """
        collector = InvocationStatsCollector("deep_research")
        nested_invocation = LanguageModelInvocationStats.from_usage(
            model_name="gemini-test",
            token_usage=LanguageModelTokenUsage(
                prompt_tokens=8,
                completion_tokens=2,
                total_tokens=10,
            ),
            source="web_search.grounding.vertexai",
        )

        with collector.scope() as invocation_stats:
            collector.record_invocation_stats([nested_invocation])

        assert invocation_stats == [nested_invocation]

    @pytest.mark.ai
    def test_record_language_model_response__uses_usage_attribute(self) -> None:
        """
        Purpose: Verify toolkit/OpenAI responses that expose `.usage` are recorded.
        Why this matters: This is the common Unique Toolkit language-model response shape.
        Setup summary: Record a response with `.usage` and assert normalized token fields.
        """
        collector = InvocationStatsCollector("web_search")
        response = SimpleNamespace(usage=_usage(13))

        with collector.scope() as invocation_stats:
            collector.record_language_model_response(
                model_name="gpt-test",
                response=response,
                source="web_search.structured_llm",
            )

        assert len(invocation_stats) == 1
        assert invocation_stats[0].token_usage.prompt_tokens == 13
        assert invocation_stats[0].token_usage.completion_tokens == 1
        assert invocation_stats[0].token_usage.total_tokens == 14

    @pytest.mark.ai
    def test_record_language_model_response__uses_usage_metadata__when_usage_missing(
        self,
    ) -> None:
        """
        Purpose: Verify LangChain `usage_metadata` is accepted when `.usage` is absent.
        Why this matters: Provider adapters do not all populate a toolkit `.usage` field.
        Setup summary: Record usage_metadata with LangChain token names and assert mapping.
        """
        collector = InvocationStatsCollector("deep_research")
        response = SimpleNamespace(
            usage_metadata={
                "input_tokens": 9,
                "output_tokens": 1,
                "total_tokens": 10,
            }
        )

        with collector.scope() as invocation_stats:
            collector.record_language_model_response(
                model_name="gpt-test",
                response=response,
                source="deep_research.test.9",
            )

        assert len(invocation_stats) == 1
        assert invocation_stats[0].token_usage.prompt_tokens == 9
        assert invocation_stats[0].token_usage.completion_tokens == 1
        assert invocation_stats[0].token_usage.total_tokens == 10

    @pytest.mark.ai
    def test_record_language_model_response__uses_response_metadata__when_usage_metadata_missing(
        self,
    ) -> None:
        """
        Purpose: Verify OpenAI-compatible LangChain response metadata is accepted as a fallback.
        Why this matters: Provider adapters do not all populate AIMessage.usage_metadata.
        Setup summary: Record response_metadata.token_usage and assert normalized toolkit fields.
        """
        collector = InvocationStatsCollector("deep_research")
        response = SimpleNamespace(
            response_metadata={
                "token_usage": {
                    "prompt_tokens": 13,
                    "completion_tokens": 5,
                    "total_tokens": 18,
                }
            }
        )

        with collector.scope() as invocation_stats:
            collector.record_language_model_response(
                model_name="gpt-test",
                response=response,
                source="deep_research.supervisor",
            )

        assert len(invocation_stats) == 1
        assert invocation_stats[0].token_usage.prompt_tokens == 13
        assert invocation_stats[0].token_usage.completion_tokens == 5
        assert invocation_stats[0].token_usage.total_tokens == 18

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_scope__isolates_parallel_runs(self) -> None:
        """
        Purpose: Verify overlapping runs cannot mix their LLM usage records.
        Why this matters: Tool instances may serve concurrent calls and must not mix billing data.
        Setup summary: Interleave two scopes, record distinct usage, and assert isolated results.
        """
        collector = InvocationStatsCollector("web_search")
        both_runs_started = asyncio.Event()
        started_runs = 0

        async def collect_usage(
            prompt_tokens: int,
        ) -> list[LanguageModelInvocationStats]:
            nonlocal started_runs
            with collector.scope() as invocation_stats:
                started_runs += 1
                if started_runs == 2:
                    both_runs_started.set()
                await both_runs_started.wait()
                collector.record_language_model_response(
                    model_name=f"model-{prompt_tokens}",
                    response=SimpleNamespace(usage=_usage(prompt_tokens)),
                    source=f"web_search.test.{prompt_tokens}",
                )
            return invocation_stats

        first, second = await asyncio.gather(collect_usage(3), collect_usage(9))

        assert [stat.source for stat in first] == ["web_search.test.3"]
        assert first[0].token_usage.prompt_tokens == 3
        assert [stat.source for stat in second] == ["web_search.test.9"]
        assert second[0].token_usage.prompt_tokens == 9

    @pytest.mark.ai
    def test_scope__keeps_distinct_namespaces_independent(self) -> None:
        """
        Purpose: Verify two collectors can be active at once without mixing stats.
        Why this matters: Deep Research opens a Web Search scope while its own scope is active.
        Setup summary: Nest two namespaces, record into each, and assert both lists stay distinct.
        """
        outer = InvocationStatsCollector("deep_research")
        inner = InvocationStatsCollector("web_search")

        with outer.scope() as outer_stats, inner.scope() as inner_stats:
            inner.record_token_usage(
                model_name="gemini-test",
                usage=_usage(8),
                source="web_search.grounding.vertexai",
            )
            outer.record_token_usage(
                model_name="gpt-test",
                usage=_usage(3),
                source="deep_research.supervisor",
            )

        assert [stat.source for stat in outer_stats] == ["deep_research.supervisor"]
        assert [stat.source for stat in inner_stats] == [
            "web_search.grounding.vertexai"
        ]
