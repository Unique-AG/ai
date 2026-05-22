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
    async def test_select_relevant_fallback_on_llm_failure_returns_all(self):
        """On LLM failure, return ALL results unmodified — never silently truncate."""
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
        # max_urls_to_select=2 must NOT cause truncation on failure
        config = SnippetJudgeConfig(max_urls_to_select=2)

        selected = await select_relevant(
            objective="Find",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        # All 4 original results, in original order
        assert len(selected) == 4
        assert [r.url for r in selected] == [
            "https://u0.com",
            "https://u1.com",
            "https://u2.com",
            "https://u3.com",
        ]

    @pytest.mark.asyncio
    async def test_select_relevant_min_score_drops_low_results(self):
        """Results below min_score are dropped entirely, not padded into top-k."""
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="B", snippet="", content=""),
            WebSearchResult(url="https://c.com", title="C", snippet="", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Only index 0 is above the 0.5 threshold
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "High", "relevance_score": 0.9},
                {"index": 1, "explanation": "Low", "relevance_score": 0.2},
                {"index": 2, "explanation": "Low", "relevance_score": 0.1},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=5, min_score=0.5)

        selected = await select_relevant(
            objective="Find best",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        assert len(selected) == 1
        assert selected[0].url == "https://a.com"

    @pytest.mark.asyncio
    async def test_select_relevant_all_below_min_score_returns_empty(self):
        """If every result scores below min_score, return empty (signal, not failure)."""
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="B", snippet="", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "Low", "relevance_score": 0.1},
                {"index": 1, "explanation": "Low", "relevance_score": 0.2},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=5, min_score=0.5)

        selected = await select_relevant(
            objective="Find best",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        assert selected == []

    @pytest.mark.asyncio
    async def test_select_relevant_passes_query_and_gap_to_prompt(self):
        """When query and gap are provided, they appear in the rendered user prompt."""
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="S", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [{"index": 0, "explanation": "Ok", "relevance_score": 0.9}],
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        await select_relevant(
            objective="Find recent Stripe pricing",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            query="stripe international card transaction fee 2026",
            gap="Stripe cross-border fee percentage",
        )

        call_args = mock_lm_service.complete_async.call_args
        messages = call_args[0][0]
        user_content = (
            messages[1].content if hasattr(messages[1], "content") else str(messages[1])
        )
        assert "stripe international card transaction fee 2026" in user_content
        assert "Stripe cross-border fee percentage" in user_content

    @pytest.mark.asyncio
    async def test_select_relevant_attaches_scores_to_returned_results(self):
        """Each selected result carries its judge ``relevance_score`` for the agent.

        The agent uses this signal (≥0.85 → prefer fetch over another search)
        so it must round-trip from the LLM judgment to the returned
        WebSearchResult, in ranked order.
        """
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="B", snippet="", content=""),
            WebSearchResult(url="https://c.com", title="C", snippet="", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "mid", "relevance_score": 0.55},
                {"index": 1, "explanation": "top", "relevance_score": 0.92},
                {"index": 2, "explanation": "weak", "relevance_score": 0.35},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=5)

        selected = await select_relevant(
            objective="X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        # Ranked order: b (0.92) > a (0.55) > c (0.35); scores attached.
        assert [r.url for r in selected] == [
            "https://b.com",
            "https://a.com",
            "https://c.com",
        ]
        assert [r.relevance_score for r in selected] == [0.92, 0.55, 0.35]

    @pytest.mark.asyncio
    async def test_select_relevant_no_scores_on_llm_failure(self):
        """LLM-failure fallback returns unscored results — agent gets no false signal."""
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="B", snippet="", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_lm_service.complete_async = AsyncMock(
            side_effect=RuntimeError("LLM error")
        )

        selected = await select_relevant(
            objective="X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
        )

        # Fallback returns all results, unscored — agent must not see a stale score.
        assert len(selected) == 2
        assert all(r.relevance_score is None for r in selected)


class TestMissingJudgmentFallback:
    """Behavior when the LLM omits judgments for some result indices.

    The fallback score is tied to ``cfg.min_score`` so omitted results land
    *at the threshold floor*: kept (we never silently drop URLs the LLM
    forgot), but ranking below every explicitly-passing result and *never
    outranking* an explicit low score (those are below the threshold and
    are dropped entirely).
    """

    @pytest.mark.asyncio
    async def test_missing_judgments_default_to_min_score(self):
        """Result indices absent from the LLM response get score == cfg.min_score."""
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="B", snippet="", content=""),
            WebSearchResult(url="https://c.com", title="C", snippet="", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # LLM scored only index 0; indices 1 and 2 are omitted.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "high", "relevance_score": 0.9},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=5, min_score=0.3)

        judgments = await score_and_explain(
            objective="X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        # Index 0 keeps its explicit score; 1 and 2 get the threshold floor (0.3).
        assert judgments[0].relevance_score == 0.9
        assert judgments[1].relevance_score == 0.3
        assert judgments[2].relevance_score == 0.3

    @pytest.mark.asyncio
    async def test_missing_judgment_does_not_outrank_explicit_low(self):
        """An explicitly low-scored result (< min_score) is dropped, so it cannot
        be outranked — the asymmetry Cursor flagged is gone by construction.
        """
        results = [
            WebSearchResult(url="https://a.com", title="A", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="B", snippet="", content=""),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Index 0 omitted; index 1 explicitly scored low (below min_score
        # but above the clearly-irrelevant threshold of 0.15 — anything below
        # that triggers the off-topic raise instead of falling open).
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 1, "explanation": "low", "relevance_score": 0.2},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=5, min_score=0.3)

        selected = await select_relevant(
            objective="X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        # The omitted index 0 is kept at the floor (0.3 == min_score).
        # The explicit low index 1 is dropped (0.2 < min_score).
        # There is no scenario in which 0.2 outranks 0.3 because 0.2 is gone.
        assert [r.url for r in selected] == ["https://a.com"]

    @pytest.mark.asyncio
    async def test_missing_judgment_ranks_below_explicit_passing(self):
        """An explicitly high-scored result ranks above a missing-judgment one."""
        results = [
            WebSearchResult(
                url="https://missing.com", title="M", snippet="", content=""
            ),
            WebSearchResult(
                url="https://explicit.com", title="E", snippet="", content=""
            ),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Only index 1 scored (above floor); index 0 omitted.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 1, "explanation": "high", "relevance_score": 0.8},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=5, min_score=0.3)

        selected = await select_relevant(
            objective="X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=config,
        )

        # Explicit high (0.8) ranks first; missing (0.3 floor) second.
        assert [r.url for r in selected] == [
            "https://explicit.com",
            "https://missing.com",
        ]

    @pytest.mark.asyncio
    async def test_all_missing_judgments_raise_serp_off_topic(self):
        """If *every* index is missing (LLM returned ``judgments=[]``),
        ``select_relevant`` raises ``SerpOffTopicError`` instead of falling
        open.

        Historical context: the previous behaviour was to fall open with the
        full unscored list, on the theory that "padding all slots at
        ``cfg.min_score`` would let every result pass ranking silently and
        the executor's unfiltered-SERP fallback would never fire." That was
        safer than silent ranking-pass, but production traces showed the
        unfiltered list it surfaced was almost always garbage (LinkedIn
        profiles, RICS pages, off-topic Facebook posts) — and the agent
        either chased those URLs or got confused. Distinguishing "judge
        truly said nothing" from "judge failed mid-parse" lets the V3
        executor short-circuit with a "reformulate" cue on the first case
        while preserving fail-open on the second.
        """
        from unique_web_search.services.snippet_judge import SerpOffTopicError

        results = [
            WebSearchResult(url=f"https://u{i}.com", title="", snippet="", content="")
            for i in range(3)
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # LLM returned an empty judgments list — the structural off-topic
        # signal we now propagate (not the same as a parse failure).
        mock_response.choices[0].message.parsed = {"judgments": []}
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)
        config = SnippetJudgeConfig(max_urls_to_select=2, min_score=0.3)

        with pytest.raises(SerpOffTopicError):
            await select_relevant(
                objective="X",
                results=results,
                language_model_service=mock_lm_service,
                language_model=mock_lm,
                config=config,
            )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_all_below_clearly_irrelevant_threshold_raises_off_topic(self):
        """If every judgment lands below the 0.15 "clearly irrelevant" band,
        raise ``SerpOffTopicError`` instead of falling back to the unfiltered
        SERP.

        Real production trace this catches: Khlong Toei sale-price query iter
        4. Garbled-Thai query yielded pubmed chemistry papers; the judge
        scored every result in the 0.0-0.1 range; the executor fell back to
        unfiltered and the agent received 5 unrelated URLs. The "max score
        across by_index" check routes this case through the same reformulate
        cue as the empty-judgments case — same exception, same downstream
        executor handler, different log line.

        The 0.15 threshold mirrors the judge prompt's calibration band
        boundary (0.00-0.14 = "forum thread, social media, off-topic,
        broken/spam" vs 0.15-0.39 = "weak match"). Anything ≥0.15 stays on
        the existing fall-back path.
        """
        from unique_web_search.services.snippet_judge import SerpOffTopicError

        results = [
            WebSearchResult(url=f"https://u{i}.com", title="", snippet="", content="")
            for i in range(3)
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # Every result scored in the "clearly irrelevant" band.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "off-topic", "relevance_score": 0.05},
                {"index": 1, "explanation": "off-topic", "relevance_score": 0.10},
                {"index": 2, "explanation": "off-topic", "relevance_score": 0.12},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        with pytest.raises(SerpOffTopicError):
            await select_relevant(
                objective="X",
                results=results,
                language_model_service=mock_lm_service,
                language_model=mock_lm,
                config=SnippetJudgeConfig(min_score=0.3),
            )

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_max_score_at_threshold_does_not_raise_off_topic(self):
        """A single judgment at exactly 0.15 (band boundary) is "weak but
        possibly useful" — keep the existing fall-back-to-unfiltered behaviour
        rather than treating the SERP as off-topic.

        This locks the boundary: ``< 0.15`` routes to off-topic, ``>= 0.15``
        does not. If someone shifts the comparator or the constant, the test
        flags the calibration desync.
        """
        results = [
            WebSearchResult(url=f"https://u{i}.com", title="", snippet="", content="")
            for i in range(3)
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        # One result at exactly the threshold, others below — but the max IS
        # at the threshold, so it must NOT raise.
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "weak", "relevance_score": 0.05},
                {"index": 1, "explanation": "weak", "relevance_score": 0.15},
                {"index": 2, "explanation": "weak", "relevance_score": 0.10},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        # min_score=0.3 means *all* results still get filtered out at the
        # ranking step. The test isn't asserting executor behaviour
        # (fall-back-to-unfiltered lives there, not here) — only that the
        # judge does NOT raise off-topic for a max-score that hits the
        # band boundary exactly. ``select_relevant`` returns an empty list
        # in that case, and the executor turns that into the existing
        # unfiltered-SERP fallback via its own ``if not filtered`` branch.
        selected = await select_relevant(
            objective="X",
            results=results,
            language_model_service=mock_lm_service,
            language_model=mock_lm,
            config=SnippetJudgeConfig(min_score=0.3),
        )
        # Empty list, NOT a raise — that's the calibration boundary working.
        assert selected == []

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_clearly_irrelevant_logs_diagnostic_with_max_score(self, caplog):
        """The new clearly-irrelevant path must log the max score + URLs so
        operators can confirm in production logs that the judge really did
        score everything in the 0.0-0.14 band (vs the empty-judgments case,
        which is logged separately)."""
        import logging

        from unique_web_search.services.snippet_judge import SerpOffTopicError

        results = [
            WebSearchResult(
                url="https://pubmed.ncbi.nlm.nih.gov/some/paper",
                title="A chemistry paper",
                snippet="",
                content="",
            ),
            WebSearchResult(
                url="https://example.com/off-topic",
                title="Off-topic page",
                snippet="",
                content="",
            ),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {
            "judgments": [
                {"index": 0, "explanation": "off-topic", "relevance_score": 0.07},
                {"index": 1, "explanation": "off-topic", "relevance_score": 0.03},
            ]
        }
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        with caplog.at_level(
            logging.WARNING,
            logger="unique_web_search.services.snippet_judge.service",
        ):
            with pytest.raises(SerpOffTopicError):
                await select_relevant(
                    objective="X",
                    results=results,
                    language_model_service=mock_lm_service,
                    language_model=mock_lm,
                    config=SnippetJudgeConfig(),
                )

        # The clearly-irrelevant log must fire (different from the empty-
        # judgments log so operators can distinguish the two paths).
        matching = [
            r for r in caplog.records if "clearly-irrelevant band" in r.getMessage()
        ]
        assert matching, f"Expected diagnostic log, got: {caplog.records}"
        msg = matching[0].getMessage()
        # Max score + URLs must be in the log for production diagnosis.
        assert "max=0.07" in msg
        assert "pubmed.ncbi.nlm.nih.gov/some/paper" in msg
        assert "example.com/off-topic" in msg

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_empty_judgments_logs_diagnostic_with_urls(self, caplog):
        """When the judge bails silently (empty judgments), the URLs must be
        logged so operators can pattern-match which SERPs break it.

        Production traces showed ``before=N, after=N, kept_scores={}`` at the
        executor level with *no* signal on which URLs the LLM skipped — making
        the failure undiagnosable. Lock in that diagnostic: the WARNING log
        must include the URLs so future BNPP-style failures are traceable to
        a content pattern (social media, PDFs, etc).
        """
        import logging

        results = [
            WebSearchResult(
                url="https://facebook.com/some/post",
                title="A Facebook post",
                snippet="",
                content="",
            ),
            WebSearchResult(
                url="https://example.com/report.pdf",
                title="A PDF report",
                snippet="",
                content="",
            ),
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = {"judgments": []}
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        from unique_web_search.services.snippet_judge import SerpOffTopicError

        with caplog.at_level(
            logging.WARNING,
            logger="unique_web_search.services.snippet_judge.service",
        ):
            # ``select_relevant`` now propagates ``SerpOffTopicError`` for the
            # raw-judgments=0 case (the executor catches it to surface a
            # reformulate cue). We still need to verify the diagnostic
            # WARNING log fires on the way out — that's what gives operators
            # actionable signal regardless of whether the caller opts into
            # the new propagation behaviour.
            with pytest.raises(SerpOffTopicError):
                await select_relevant(
                    objective="X",
                    results=results,
                    language_model_service=mock_lm_service,
                    language_model=mock_lm,
                    config=SnippetJudgeConfig(),
                )

        # The "0 usable judgments" log must fire and include the URLs.
        matching = [r for r in caplog.records if "0 usable judgments" in r.getMessage()]
        assert matching, f"Expected diagnostic log, got: {caplog.records}"
        msg = matching[0].getMessage()
        assert "facebook.com/some/post" in msg
        assert "example.com/report.pdf" in msg

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_parsed_none_logs_diagnostic_with_titles(self, caplog):
        """When structured-output decoding returns ``parsed=None`` (refusal,
        schema mismatch, empty completion), the first few titles must be
        logged so operators can spot the content-type pattern that broke the
        decoder. Without this log, the failure is invisible above the
        ``select_relevant`` ``except`` line."""
        import logging

        results = [
            WebSearchResult(
                url=f"https://u{i}.example/post",
                title=f"Title {i}",
                snippet="",
                content="",
            )
            for i in range(3)
        ]
        mock_lm_service = Mock()
        mock_lm = Mock()
        mock_lm.name = "test-model"
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.parsed = None
        mock_lm_service.complete_async = AsyncMock(return_value=mock_response)

        with caplog.at_level(
            logging.WARNING,
            logger="unique_web_search.services.snippet_judge.service",
        ):
            await select_relevant(
                objective="X",
                results=results,
                language_model_service=mock_lm_service,
                language_model=mock_lm,
                config=SnippetJudgeConfig(),
            )

        matching = [
            r
            for r in caplog.records
            if "structured output parsing returned None" in r.getMessage()
        ]
        assert matching, f"Expected diagnostic log, got: {caplog.records}"
        msg = matching[0].getMessage()
        assert "Title 0" in msg
        assert "Title 1" in msg


class TestRankAndSelectMinScore:
    """Stage 2: ``min_score`` threshold filtering."""

    def test_rank_and_select_min_score_drops_below_threshold(self):
        """Judgments with score < min_score are excluded; higher ones kept."""
        judgments = [
            SnippetJudgment(index=0, explanation="", relevance_score=0.9),
            SnippetJudgment(index=1, explanation="", relevance_score=0.4),
            SnippetJudgment(index=2, explanation="", relevance_score=0.2),
        ]
        results = [
            WebSearchResult(url=f"https://d{i}.com", title="", snippet="", content="")
            for i in range(3)
        ]

        result = rank_and_select(
            judgments,
            results,
            max_urls_to_select=5,
            max_results_per_domain=2,
            min_score=0.5,
        )

        assert result == [0]

    def test_rank_and_select_min_score_zero_keeps_all(self):
        """min_score=0.0 (default) keeps every judgment regardless of score."""
        judgments = [
            SnippetJudgment(index=0, explanation="", relevance_score=0.05),
            SnippetJudgment(index=1, explanation="", relevance_score=0.0),
        ]
        results = [
            WebSearchResult(url="https://a.com", title="", snippet="", content=""),
            WebSearchResult(url="https://b.com", title="", snippet="", content=""),
        ]

        result = rank_and_select(
            judgments,
            results,
            max_urls_to_select=5,
            max_results_per_domain=2,
            min_score=0.0,
        )

        assert result == [0, 1]
