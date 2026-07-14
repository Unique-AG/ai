import warnings

import pytest
from pydantic import ValidationError

from unique_toolkit.language_model.infos import LanguageModelName
from unique_toolkit.language_model.invocation_stats import (
    LanguageModelInvocationReport,
    LanguageModelInvocationStats,
)
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

        assert stats.model_info == "gpt-4-test"
        assert stats.token_usage == usage
        assert stats.source == "main_loop"

    @pytest.mark.ai
    def test_from_usage__source_required(self) -> None:
        usage = LanguageModelTokenUsage(
            completion_tokens=1, prompt_tokens=2, total_tokens=3
        )

        with pytest.raises(TypeError):
            LanguageModelInvocationStats.from_usage("gpt-4-test", usage)  # type: ignore[call-arg]


class TestLanguageModelInvocationReportTotals:
    @pytest.mark.ai
    def test_empty_invocations__total_is_none(self) -> None:
        report = LanguageModelInvocationReport()

        assert report.invocations == []
        assert report.total_token_usage is None

    @pytest.mark.ai
    def test_multiple_invocations__total_token_usage_sums_across_all(self) -> None:
        stats_a = LanguageModelInvocationStats(
            model_info="gpt-4-test",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="main_loop",
        )
        stats_b = LanguageModelInvocationStats(
            model_info="gpt-4-test",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=2, total_tokens=3
            ),
            source="hallucination",
        )
        report = LanguageModelInvocationReport(invocations=[stats_a, stats_b])

        assert report.total_token_usage == LanguageModelTokenUsage(
            completion_tokens=11, prompt_tokens=22, total_tokens=33
        )


class TestLanguageModelInvocationReportSerialization:
    @pytest.mark.ai
    def test_model_dump_by_alias__camel_case_shape(self) -> None:
        stats = LanguageModelInvocationStats(
            model_info="gpt-4-test",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=10, prompt_tokens=20, total_tokens=30
            ),
            source="main_loop",
        )
        report = LanguageModelInvocationReport(invocations=[stats])

        dumped = report.model_dump(by_alias=True)

        assert dumped == {
            "invocations": [
                {
                    "modelInfo": "gpt-4-test",
                    "tokenUsage": {
                        "completionTokens": 10,
                        "promptTokens": 20,
                        "totalTokens": 30,
                    },
                    "source": "main_loop",
                }
            ],
            "totalTokenUsage": {
                "completionTokens": 10,
                "promptTokens": 20,
                "totalTokens": 30,
            },
        }

    @pytest.mark.ai
    def test_model_dump_by_alias__empty_report(self) -> None:
        report = LanguageModelInvocationReport()

        dumped = report.model_dump(by_alias=True)

        assert dumped == {
            "invocations": [],
            "totalTokenUsage": None,
        }


class TestLanguageModelInvocationStatsModelInfo:
    @pytest.mark.ai
    def test_model_info__accepts_language_model_name_enum__dumps_as_plain_string(
        self,
    ) -> None:
        stats = LanguageModelInvocationStats(
            model_info=LanguageModelName.AZURE_GPT_4o_2024_1120,
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert stats.model_info == LanguageModelName.AZURE_GPT_4o_2024_1120

        dumped = stats.model_dump(by_alias=True)
        assert dumped["modelInfo"] == LanguageModelName.AZURE_GPT_4o_2024_1120.value
        assert isinstance(dumped["modelInfo"], str)

    @pytest.mark.ai
    def test_model_info__accepts_arbitrary_string(self) -> None:
        stats = LanguageModelInvocationStats(
            model_info="some-custom-model-id",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert stats.model_info == "some-custom-model-id"
        assert stats.model_dump(by_alias=True)["modelInfo"] == "some-custom-model-id"

    @pytest.mark.ai
    def test_model_info__string_matching_known_name__normalized_to_enum(self) -> None:
        """Capture sites pass `.name` strings; a string that matches a
        `LanguageModelName` value must canonicalize to the enum so the same
        model never appears as both enum and str across entries."""
        stats = LanguageModelInvocationStats(
            model_info=LanguageModelName.AZURE_GPT_4o_2024_1120.value,
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert isinstance(stats.model_info, LanguageModelName)
        assert stats.model_info is LanguageModelName.AZURE_GPT_4o_2024_1120

    @pytest.mark.ai
    def test_model_info__string_is_stripped(self) -> None:
        stats = LanguageModelInvocationStats(
            model_info="  some-custom-model-id  ",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="main_loop",
        )

        assert stats.model_info == "some-custom-model-id"

    @pytest.mark.ai
    def test_model_info__empty_string__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_info="   ",
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
                model_info="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
            )  # type: ignore[call-arg]

    @pytest.mark.ai
    def test_source__empty_string__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_info="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
                source="",
            )

    @pytest.mark.ai
    def test_source__whitespace_only__raises(self) -> None:
        with pytest.raises(ValidationError):
            LanguageModelInvocationStats(
                model_info="gpt-4-test",
                token_usage=LanguageModelTokenUsage(
                    completion_tokens=1, prompt_tokens=1, total_tokens=2
                ),
                source="   ",
            )

    @pytest.mark.ai
    def test_source__is_stripped(self) -> None:
        stats = LanguageModelInvocationStats(
            model_info="gpt-4-test",
            token_usage=LanguageModelTokenUsage(
                completion_tokens=1, prompt_tokens=1, total_tokens=2
            ),
            source="  main_loop  ",
        )

        assert stats.source == "main_loop"


class TestLanguageModelInvocationStatsNoProtectedNamespaceWarning:
    @pytest.mark.ai
    def test_construction__emits_no_protected_namespace_warning(self) -> None:
        """`model_info` starts with `model_` which pydantic normally flags as
        a protected-namespace clash; `protected_namespaces=()` on the shared
        model_config must silence that warning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            LanguageModelInvocationStats(
                model_info="gpt-4-test",
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

    @pytest.mark.ai
    def test_report_construction__emits_no_protected_namespace_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            LanguageModelInvocationReport()

        protected_namespace_warnings = [
            warning
            for warning in caught
            if "protected namespace" in str(warning.message)
        ]
        assert protected_namespace_warnings == []
