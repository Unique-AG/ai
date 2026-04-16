"""Tests for shared grounding response parsing (Bing + VertexAI)."""

from unittest.mock import AsyncMock

import pytest

from unique_web_search.services.search_engine.schema import WebSearchResult
from unique_web_search.services.search_engine.utils.grounding import (
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
    async def test_convert__first_fails__falls_back_to_second(self) -> None:
        expected = [
            WebSearchResult(url="https://b.com", title="B", snippet="s", content="c")
        ]
        strategy_1 = AsyncMock(side_effect=ValueError("parse error"))
        strategy_2 = AsyncMock(return_value=expected)

        results = await convert_response_to_search_results(
            "some response", [strategy_1, strategy_2]
        )

        assert results == expected
        strategy_1.assert_called_once()
        strategy_2.assert_called_once()

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
