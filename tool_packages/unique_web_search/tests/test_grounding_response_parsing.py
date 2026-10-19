"""Tests for shared grounding response parsing (Bing + VertexAI)."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from unique_search_proxy_core.schema import GroundingCitation

from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding import (
    CitationAwareLLMParserStrategy,
    convert_response_to_search_results,
)


class TestConvertResponseToSearchResults:
    """Strategy-chain conversion lives in ``grounding.response_parsing``."""

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_convert__first_strategy_succeeds__returns_immediately(self) -> None:
        expected = [
            WebSearchResult(url="https://a.com", title="A", snippet="s", content="c")
        ]
        strategy_1 = AsyncMock(return_value=expected)
        strategy_2 = AsyncMock()

        results = await convert_response_to_search_results(
            "some response", [strategy_1, strategy_2]
        )

        assert results == expected
        strategy_1.assert_called_once_with("some response")
        strategy_2.assert_not_called()

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_convert__first_fails__falls_back_to_second(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        expected = [
            WebSearchResult(url="https://b.com", title="B", snippet="s", content="c")
        ]
        strategy_1 = AsyncMock(side_effect=ValueError("parse error"))
        strategy_2 = AsyncMock(return_value=expected)

        with caplog.at_level(logging.INFO):
            results = await convert_response_to_search_results(
                "some response", [strategy_1, strategy_2]
            )

        assert results == expected
        strategy_1.assert_called_once()
        strategy_2.assert_called_once()
        assert "strategy_index=0 fallback=False" in caplog.text
        assert "strategy_index=1 fallback=True" in caplog.text
        assert "result_urls=['https://b.com']" in caplog.text

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_convert__all_strategies_fail__raises_value_error(self) -> None:
        strategy_1 = AsyncMock(side_effect=ValueError("no JSON"))
        strategy_2 = AsyncMock(side_effect=RuntimeError("LLM failure"))

        with pytest.raises(ValueError) as exc_info:
            await convert_response_to_search_results(
                "bad response", [strategy_1, strategy_2]
            )
        assert "No conversion strategy found" in str(exc_info.value)


class TestCitationAwareLLMParserStrategy:
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_uses_annotation_urls_instead_of_model_urls(self) -> None:
        response = "First source claim [1]. Second source claim [2]."
        citations = [
            GroundingCitation(
                url="https://canonical.example/one",
                title="Source one",
                marker="[1]",
                start_index=19,
                end_index=22,
            ),
            GroundingCitation(
                url="https://canonical.example/two",
                title="Source two",
                marker="[2]",
                start_index=44,
                end_index=47,
            ),
        ]
        parsed = {
            "results": [
                {
                    "source_id": "SOURCE_0",
                    "detailed_answer": "First source claim.",
                    "key_facts": ["First fact"],
                },
                {
                    "source_id": "SOURCE_1",
                    "detailed_answer": "Second source claim.",
                    "key_facts": ["Second fact"],
                },
            ]
        }
        llm_response = MagicMock()
        llm_response.choices[0].message.parsed = parsed
        llm_service = MagicMock()
        llm_service.complete_async = AsyncMock(return_value=llm_response)
        llm = MagicMock(name="test-model")
        llm.name = "test-model"
        strategy = CitationAwareLLMParserStrategy(llm, llm_service)

        results = await strategy(response, citations)

        assert [result.url for result in results] == [
            "https://canonical.example/one",
            "https://canonical.example/two",
        ]
        assert [result.title for result in results] == ["Source one", "Source two"]
        messages = llm_service.complete_async.await_args.kwargs["messages"]
        assert "https://canonical.example" not in str(messages)
        assert "SOURCE_0" in str(messages)
        assert "SOURCE_1" in str(messages)

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_rejects_citation_whose_offset_does_not_match_marker(self) -> None:
        citation = GroundingCitation(
            url="https://canonical.example/source",
            title="Source",
            marker="[1]",
            start_index=0,
            end_index=3,
        )
        strategy = CitationAwareLLMParserStrategy(MagicMock(), MagicMock())

        with pytest.raises(ValueError, match="No valid grounding citations"):
            await strategy("Claim [1]", [citation])

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_preserves_cited_prose_for_unknown_source_id(self) -> None:
        citation = GroundingCitation(
            url="https://canonical.example/source",
            title="Source",
            marker="[1]",
            start_index=6,
            end_index=9,
        )
        llm_response = MagicMock()
        llm_response.choices[0].message.parsed = {
            "results": [
                {
                    "source_id": "SOURCE_99",
                    "detailed_answer": "Claim.",
                    "key_facts": [],
                }
            ]
        }
        llm_service = MagicMock()
        llm_service.complete_async = AsyncMock(return_value=llm_response)
        strategy = CitationAwareLLMParserStrategy(MagicMock(), llm_service)

        results = await strategy("Claim [1]", [citation])

        assert len(results) == 1
        assert results[0].url == "https://canonical.example/source"
        assert results[0].content == "Claim"

    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_preserves_all_sources_when_structuring_model_omits_one(
        self,
    ) -> None:
        response = "First [1]. Second [2]."
        citations = [
            GroundingCitation(
                url="https://canonical.example/one",
                title="One",
                marker="[1]",
                start_index=6,
                end_index=9,
            ),
            GroundingCitation(
                url="https://canonical.example/two",
                title="Two",
                marker="[2]",
                start_index=18,
                end_index=21,
            ),
        ]
        llm_response = MagicMock()
        llm_response.choices[0].message.parsed = {
            "results": [
                {
                    "source_id": "SOURCE_0",
                    "detailed_answer": "First.",
                    "key_facts": [],
                }
            ]
        }
        llm_service = MagicMock()
        llm_service.complete_async = AsyncMock(return_value=llm_response)
        strategy = CitationAwareLLMParserStrategy(MagicMock(), llm_service)

        results = await strategy(response, citations)

        assert [result.url for result in results] == [
            "https://canonical.example/one",
            "https://canonical.example/two",
        ]
        assert results[0].content == "First . Second ."
        assert results[1].content == "First . Second ."
