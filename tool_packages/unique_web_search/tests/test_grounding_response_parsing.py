"""Tests for shared grounding response parsing (Bing + VertexAI)."""

import logging
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
    async def test_convert__first_fails__falls_back_to_second(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        expected = [
            WebSearchResult(url="https://b.com", title="B", snippet="s", content="c")
        ]
        strategy_1 = AsyncMock(side_effect=ValueError("parse error near secret"))
        strategy_2 = AsyncMock(return_value=expected)

        with caplog.at_level(logging.INFO):
            results = await convert_response_to_search_results(
                "some response", [strategy_1, strategy_2]
            )

        assert results == expected
        strategy_1.assert_called_once()
        strategy_2.assert_called_once()
        assert "strategy_index=0 fallback=False" in caplog.text
        assert "error_type=ValueError" in caplog.text
        assert "strategy_index=1 fallback=True" in caplog.text
        assert "result_count=1" in caplog.text
        assert "https://b.com" not in caplog.text
        assert "secret" not in caplog.text

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
