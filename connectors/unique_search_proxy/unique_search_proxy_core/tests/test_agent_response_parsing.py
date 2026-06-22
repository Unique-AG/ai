"""Tests for agent-search response parsing strategies."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unique_search_proxy_core.agent_engines.output_schema import (
    AgentSearchOutput,
    AgentSearchOutputResultItem,
)
from unique_search_proxy_core.agent_engines.response_parsing import (
    JsonConversionStrategy,
    LLMParserStrategy,
    convert_response_to_search_results,
)
from unique_search_proxy_core.schema import WebSearchResult


class TestConvertResponseToSearchResults:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_convert__first_strategy_succeeds__returns_immediately(self) -> None:
        expected = [
            WebSearchResult(url="https://a.com", title="A", snippet="s", content="c"),
        ]
        strategy_1 = AsyncMock(return_value=expected)
        strategy_2 = AsyncMock()

        results = await convert_response_to_search_results(
            "some response",
            [strategy_1, strategy_2],
        )

        assert results == expected
        strategy_1.assert_called_once_with("some response")
        strategy_2.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_convert__first_fails__falls_back_to_second(self) -> None:
        expected = [
            WebSearchResult(url="https://b.com", title="B", snippet="s", content="c"),
        ]
        strategy_1 = AsyncMock(side_effect=ValueError("parse error"))
        strategy_2 = AsyncMock(return_value=expected)

        results = await convert_response_to_search_results(
            "some response",
            [strategy_1, strategy_2],
        )

        assert results == expected
        strategy_1.assert_called_once()
        strategy_2.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_convert__all_strategies_fail__raises_value_error(self) -> None:
        strategy_1 = AsyncMock(side_effect=ValueError("no JSON"))
        strategy_2 = AsyncMock(side_effect=RuntimeError("LLM failure"))

        with pytest.raises(ValueError, match="No conversion strategy found"):
            await convert_response_to_search_results(
                "bad response",
                [strategy_1, strategy_2],
            )


class TestJsonConversionStrategy:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__valid_json_fence__returns_web_search_results(self) -> None:
        output = AgentSearchOutput(
            results=[
                AgentSearchOutputResultItem(
                    source_url="https://example.com/article",
                    source_title="Example Article",
                    detailed_answer="Full content",
                    key_facts=["Snippet one", "Snippet two"],
                ),
                AgentSearchOutputResultItem(
                    source_url="https://example.com/other",
                    source_title="Other Article",
                    detailed_answer="More content",
                    key_facts=["Other snippet"],
                ),
            ],
        )
        response = f"```json\n{output.model_dump_json()}\n```"
        strategy = JsonConversionStrategy()

        results = await strategy(response)

        assert len(results) == 2
        assert results[0].url == "https://example.com/article"
        assert results[0].snippet == "Snippet one\nSnippet two"
        assert results[0].content == "Full content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__plain_fence__returns_web_search_results(self) -> None:
        output = AgentSearchOutput(
            results=[
                AgentSearchOutputResultItem(
                    source_url="https://example.com/plain",
                    source_title="Plain Fence",
                    detailed_answer="Content",
                    key_facts=["Snippet"],
                ),
            ],
        )
        response = f"```\n{output.model_dump_json()}\n```"
        strategy = JsonConversionStrategy()

        results = await strategy(response)

        assert len(results) == 1
        assert results[0].url == "https://example.com/plain"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__json_fence_case_insensitive__returns_web_search_results(
        self,
    ) -> None:
        output = AgentSearchOutput(
            results=[
                AgentSearchOutputResultItem(
                    source_url="https://example.com/case",
                    source_title="Case Fence",
                    detailed_answer="Content",
                    key_facts=["Snippet"],
                ),
            ],
        )
        response = f"```JSON\n{output.model_dump_json()}\n```"
        strategy = JsonConversionStrategy()

        results = await strategy(response)

        assert len(results) == 1
        assert results[0].title == "Case Fence"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__bare_json_object__returns_web_search_results(self) -> None:
        output = AgentSearchOutput(
            results=[
                AgentSearchOutputResultItem(
                    source_url="https://example.com/bare",
                    source_title="Bare JSON",
                    detailed_answer="Content",
                    key_facts=["Snippet"],
                ),
            ],
        )
        strategy = JsonConversionStrategy()

        results = await strategy(output.model_dump_json())

        assert len(results) == 1
        assert results[0].url == "https://example.com/bare"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__no_json_fence__raises_value_error(self) -> None:
        strategy = JsonConversionStrategy()

        with pytest.raises(ValueError, match="No JSON found"):
            await strategy("This is a plain text answer without any JSON.")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__invalid_json_in_fence__raises_value_error(self) -> None:
        strategy = JsonConversionStrategy()

        with pytest.raises(ValueError, match="No valid JSON found"):
            await strategy('```json\n{"results": [{"invalid": true}]}\n```')


class TestAgentSearchOutputConversion:
    @pytest.mark.unit
    def test_to_web_search_results__maps_fields(self) -> None:
        output = AgentSearchOutput(
            results=[
                AgentSearchOutputResultItem(
                    source_url="https://a.com",
                    source_title="Title",
                    detailed_answer="Body",
                    key_facts=["fact 1", "fact 2"],
                ),
            ],
        )

        results = output.to_web_search_results()

        assert len(results) == 1
        assert results[0] == WebSearchResult(
            url="https://a.com",
            title="Title",
            snippet="fact 1\nfact 2",
            content="Body",
        )


class TestLLMParserStrategy:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__successful_parse__returns_results(self) -> None:
        mock_lmi = MagicMock()
        mock_lmi.name = "gpt-4o"
        mock_service = MagicMock()

        parsed_data = AgentSearchOutput(
            results=[
                AgentSearchOutputResultItem(
                    source_url="https://llm-parsed.com",
                    source_title="LLM Parsed",
                    detailed_answer="Parsed content",
                    key_facts=["Parsed snippet"],
                ),
            ],
        )
        mock_choice = MagicMock()
        mock_choice.message.parsed = parsed_data.model_dump()
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_service.complete_async = AsyncMock(return_value=mock_response)

        strategy = LLMParserStrategy(llm=mock_lmi, llm_service=mock_service)

        results = await strategy("Some unstructured agent response text")

        assert len(results) == 1
        assert results[0].url == "https://llm-parsed.com"
        assert results[0].title == "LLM Parsed"
        mock_service.complete_async.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call__no_parsed_content__raises_value_error(self) -> None:
        mock_lmi = MagicMock()
        mock_lmi.name = "gpt-4o"
        mock_service = MagicMock()

        mock_choice = MagicMock()
        mock_choice.message.parsed = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_service.complete_async = AsyncMock(return_value=mock_response)

        strategy = LLMParserStrategy(llm=mock_lmi, llm_service=mock_service)

        with pytest.raises(ValueError, match="No JSON found"):
            await strategy("Some text")
