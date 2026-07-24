import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.invocation_stats import (
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
