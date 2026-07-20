from unittest.mock import MagicMock

import pytest
from unique_toolkit.language_model.invocation_stats import LanguageModelInvocationStats
from unique_toolkit.language_model.schemas import LanguageModelTokenUsage

from unique_stock_ticker.stock_ticker_postprocessor import StockTickerPostprocessor


@pytest.mark.ai
@pytest.mark.asyncio
async def test_run__existing_stats__resets_and_captures_current_run(mocker) -> None:
    """Purpose: Verify each postprocessor run exposes only its own LLM usage.
    Why this matters: Reused postprocessors must not double-count earlier invocations.
    Setup summary: Seed stale stats, append current usage in the mocked integration, and assert isolation.
    """
    event = MagicMock()
    event.company_id = "company-id"
    event.user_id = "user-id"
    event.payload.chat_id = "chat-id"
    event.payload.user_message.text = "user message"
    postprocessor = StockTickerPostprocessor(config=MagicMock(), event=event)
    stale_stats = LanguageModelInvocationStats.from_usage(
        model_name="gpt-4o",
        token_usage=LanguageModelTokenUsage(total_tokens=1),
        source="stale",
    )
    current_stats = LanguageModelInvocationStats.from_usage(
        model_name="gpt-4o",
        token_usage=LanguageModelTokenUsage(total_tokens=30),
        source="stock_ticker_detection",
    )
    postprocessor._invocation_stats.append(stale_stats)

    async def retrieve_tickers(**kwargs) -> str:
        kwargs["invocation_stats"].append(current_stats)
        return "financial chart"

    retrieve_mock = mocker.patch(
        "unique_stock_ticker.stock_ticker_postprocessor.retrieve_tickers_and_plot_history",
        side_effect=retrieve_tickers,
    )
    loop_response = MagicMock()
    loop_response.message.text = "assistant message"

    await postprocessor.run(loop_response)
    reported_stats = postprocessor.invocation_stats
    reported_stats.clear()

    assert postprocessor.invocation_stats == [current_stats]
    assert postprocessor._text == "financial chart"
    retrieve_mock.assert_awaited_once_with(
        company_id="company-id",
        user_id="user-id",
        chat_id="chat-id",
        stock_ticker_config=postprocessor._config,
        assistant_message="assistant message",
        user_message="user message",
        invocation_stats=postprocessor._invocation_stats,
    )
