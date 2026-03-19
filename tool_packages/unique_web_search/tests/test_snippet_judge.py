"""Tests for the snippet judge (score + explain, rank and select)."""

from unittest.mock import AsyncMock, Mock

import pytest

from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.snippet_judge import (
    SnippetJudgeConfig,
    rank_and_select,
    score_and_explain,
    select_relevant,
)
from unique_web_search.services.snippet_judge.schema import (
    SnippetJudgeResponse,
    SnippetJudgment,
)


class TestSnippetJudgmentSchema:
    """Test SnippetJudgment field order: explanation first, then relevance_score."""

    def test_field_order_explanation_then_score(self):
        """SnippetJudgment has explanation before relevance_score."""
        j = SnippetJudgment(
            index=0,
            explanation="Relevant to the query",
            relevance_score=0.8,
        )
        assert j.index == 0
        assert j.explanation == "Relevant to the query"
        assert j.relevance_score == 0.8

    def test_snippet_judge_response_parses(self):
        """SnippetJudgeResponse parses a list of judgments."""
        resp = SnippetJudgeResponse(
            judgments=[
                SnippetJudgment(index=0, explanation="Yes", relevance_score=0.9),
                SnippetJudgment(index=1, explanation="No", relevance_score=0.2),
            ]
        )
        assert len(resp.judgments) == 2
        assert resp.judgments[0].relevance_score == 0.9
        assert resp.judgments[1].relevance_score == 0.2


class TestRankAndSelect:
    """Stage 2: sort by score, return top-k indices."""

    def test_rank_and_select_returns_indices_sorted_by_score_desc(self):
        """Sort by relevance_score descending, return indices."""
        judgments = [
            SnippetJudgment(index=0, explanation="", relevance_score=0.3),
            SnippetJudgment(index=1, explanation="", relevance_score=0.9),
            SnippetJudgment(index=2, explanation="", relevance_score=0.5),
        ]
        results = [
            WebSearchResult(url=f"https://d{i}.com", title="", snippet="", content="")
            for i in range(3)
        ]
        result = rank_and_select(
            judgments,
            results,
            max_urls_to_select=3,
            max_results_per_domain=2,
        )
        assert result == [1, 2, 0]

    def test_rank_and_select_respects_max_urls(self):
        """Only top max_urls_to_select indices are returned."""
        judgments = [
            SnippetJudgment(index=i, explanation="", relevance_score=1.0 - i * 0.2)
            for i in range(5)
        ]
        results = [
            WebSearchResult(url=f"https://d{i}.com", title="", snippet="", content="")
            for i in range(5)
        ]
        result = rank_and_select(
            judgments,
            results,
            max_urls_to_select=2,
            max_results_per_domain=2,
        )
        assert result == [0, 1]

    def test_rank_and_select_empty_returns_empty(self):
        """Empty judgments returns empty list."""
        assert (
            rank_and_select(
                [],
                [],
                max_urls_to_select=5,
                max_results_per_domain=2,
            )
            == []
        )

    def test_rank_and_select_deduplicates_by_index(self):
        """Duplicate indices are only included once (first by score order)."""
        judgments = [
            SnippetJudgment(index=1, explanation="", relevance_score=0.9),
            SnippetJudgment(index=1, explanation="", relevance_score=0.8),
            SnippetJudgment(index=0, explanation="", relevance_score=0.7),
        ]
        results = [
            WebSearchResult(url="https://a.com", title="", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="", snippet="", content=""),
        ]
        result = rank_and_select(
            judgments,
            results,
            max_urls_to_select=3,
            max_results_per_domain=2,
        )
        assert result == [1, 0]

    def test_rank_and_select_enforces_hard_cap_per_registered_domain(self):
        """Subdomains of the same site are capped deterministically."""
        judgments = [
            SnippetJudgment(index=0, explanation="", relevance_score=0.95),
            SnippetJudgment(index=1, explanation="", relevance_score=0.9),
            SnippetJudgment(index=2, explanation="", relevance_score=0.85),
            SnippetJudgment(index=3, explanation="", relevance_score=0.8),
        ]
        results = [
            WebSearchResult(
                url="https://nvidianews.nvidia.com/a",
                title="",
                snippet="",
                content="",
            ),
            WebSearchResult(
                url="https://investor.nvidia.com/b",
                title="",
                snippet="",
                content="",
            ),
            WebSearchResult(
                url="https://blogs.nvidia.com/c",
                title="",
                snippet="",
                content="",
            ),
            WebSearchResult(
                url="https://example.com/d",
                title="",
                snippet="",
                content="",
            ),
        ]

        result = rank_and_select(
            judgments,
            results,
            max_urls_to_select=4,
            max_results_per_domain=2,
        )

        assert result == [0, 1, 3]


class TestScoreAndExplain:
    """Stage 1: LLM returns judgments."""

    @pytest.mark.asyncio
    async def test_score_and_explain_returns_judgments_from_llm(self):
        """Mock LLM returns SnippetJudgeResponse; score_and_explain returns list of judgments."""
        results = [
            WebSearchResult(
                url="https://a.com", title="A", snippet="Snippet A", content=""
            ),
            WebSearchResult(
                url="https://b.com", title="B", snippet="Snippet B", content=""
            ),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "Relevant", "relevance_score": 0.9},
                {"index": 1, "explanation": "Less relevant", "relevance_score": 0.4},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        judgments = await score_and_explain(
            objective="Find info about X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
        )

        assert len(judgments) >= 2
        assert judgments[0].relevance_score == 0.9
        assert judgments[1].relevance_score == 0.4
        mock_lm_service.complete_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_and_explain_empty_results_returns_empty(self):
        """Empty results returns empty judgments without calling LLM."""
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"

        judgments = await score_and_explain(
            objective="Anything",
            results=[],
            language_model_service=mock_lm_service,
            language_model=mock_lm,
        )

        assert judgments == []
        mock_lm_service.complete_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_score_and_explain_uses_custom_prompts_from_config(self):
        """When config provides custom system_prompt and user_prompt_template, they are used."""
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="S", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [{"index": 0, "explanation": "Ok", "relevance_score": 0.8}],
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        config = SnippetJudgeConfig(
            system_prompt="Custom system",
            user_prompt_template="Objective: {{ objective }}\nResults:\n{{ numbered_results }}",
        )
        await score_and_explain(
            objective="Find X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        mock_lm_service.complete_async.assert_called_once()
        call_args = mock_lm_service.complete_async.call_args
        messages = call_args[0][0]
        # First message is system, second is user
        system_content = (
            messages[0].content if hasattr(messages[0], "content") else str(messages[0])
        )
        user_content = (
            messages[1].content if hasattr(messages[1], "content") else str(messages[1])
        )
        assert "Custom system" in system_content
        assert "Find X" in user_content
        assert "Objective:" in user_content
        assert "Results:" in user_content


class TestSelectRelevant:
    """Integration: select_relevant returns filtered and ranked WebSearchResults."""

    @pytest.mark.asyncio
    async def test_select_relevant_returns_filtered_ranked_results(self):
        """select_relevant runs judge then returns results in ranked order."""
        results = [
            WebSearchResult(
                url="https://low.com", title="Low", snippet="Low", content=""
            ),
            WebSearchResult(
                url="https://high.com", title="High", snippet="High", content=""
            ),
            WebSearchResult(
                url="https://mid.com", title="Mid", snippet="Mid", content=""
            ),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # LLM returns: index 1 best, then 2, then 0
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "Low", "relevance_score": 0.2},
                {"index": 1, "explanation": "High", "relevance_score": 0.95},
                {"index": 2, "explanation": "Mid", "relevance_score": 0.6},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=2)

        selected = await select_relevant(
            objective="Find best",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        assert len(selected) == 2
        assert selected[0].url == "https://high.com"
        assert selected[1].url == "https://mid.com"

    @pytest.mark.asyncio
    async def test_select_relevant_fallback_on_llm_failure(self):
        """On LLM failure, fall back to first max_urls_to_select results."""
        results = [
            WebSearchResult(
                url=f"https://u{i}.com", title=f"T{i}", snippet="", content=""
            )
            for i in range(4)
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_lm_service.complete_async = AsyncMock(
            side_effect=RuntimeError("LLM error")
        )
        config = SnippetJudgeConfig(max_urls_to_select=2)

        selected = await select_relevant(
            objective="Find",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        assert len(selected) == 2
        assert selected[0].url == "https://u0.com"
        assert selected[1].url == "https://u1.com"
