from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from unique_toolkit._common.default_language_model import DEFAULT_GPT_4o
from unique_toolkit.chat import ChatService
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
)

from unique_stock_ticker.detection.config import StockTickerDetectionConfig
from unique_stock_ticker.detection.memory import StockTickerMemoryManager
from unique_stock_ticker.detection.schema import StockTicker
from unique_stock_ticker.detection.service import StockTickerService


@pytest.fixture
def mock_chat_service():
    return create_autospec(ChatService)


@pytest.fixture
def mock_llm_service():
    return create_autospec(LanguageModelService)


@pytest.fixture
def stock_ticker_config():
    # Adjust as necessary to create a real or dummy config
    return StockTickerDetectionConfig(
        language_model=LanguageModelInfo.from_name(DEFAULT_GPT_4o)
    )


@pytest.fixture
def stock_ticker_service(mock_chat_service, mock_llm_service, stock_ticker_config):
    return StockTickerService(
        language_model_service=mock_llm_service,
        config=stock_ticker_config,
    )


@pytest.fixture
def mock_all_pass_memory_manager():
    mock = MagicMock(spec=StockTickerMemoryManager)
    mock.process_new_tickers = lambda x: x
    return mock


@pytest.fixture
def mock_all_fail_memory_manager():
    mock = MagicMock(spec=StockTickerMemoryManager)
    mock.process_new_tickers.return_value = []
    return mock


@pytest.mark.asyncio
async def test_get_stock_tickers(
    stock_ticker_service,
    mock_llm_service,
    mock_all_pass_memory_manager,
    mock_all_fail_memory_manager,
):
    mock_llm_service.complete_async.return_value = AsyncMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="""
                            {
                                "tickers": [
                                    {
                                    "explanation": "",
                                    "ticker": "AAPL",
                                    "company_name": "Apple",
                                    "instrument_type": "equity"
                                    }
                                ]
                            }
                            """
                )
            )
        ]
    )

    assistant_message = "assistant message"
    user_message = "user message"

    stock_ticker_result = await stock_ticker_service.get_stock_tickers(
        assistant_message, user_message
    )
    assert stock_ticker_result.response == [
        StockTicker(
            ticker="AAPL",
            company_name="Apple",
            explanation="",
            instrument_type="equity",
        )
    ]
    mock_llm_service.complete_async.assert_called_once()

    stock_ticker_service._memory_manager = mock_all_pass_memory_manager
    stock_ticker_result = await stock_ticker_service.get_stock_tickers(
        assistant_message, user_message
    )
    assert stock_ticker_result.response == [
        StockTicker(
            ticker="AAPL",
            company_name="Apple",
            explanation="",
            instrument_type="equity",
        )
    ]

    stock_ticker_service._memory_manager = mock_all_fail_memory_manager
    stock_ticker_result = await stock_ticker_service.get_stock_tickers(
        assistant_message, user_message
    )
    assert stock_ticker_result.response == []


@pytest.mark.asyncio
async def test_get_stock_tickers_no_valid_response(
    stock_ticker_service, mock_llm_service
):
    mock_llm_service.complete_async.return_value = AsyncMock(
        choices=[MagicMock(message=MagicMock(content=""))]
    )

    assistant_message = "assistant message"
    user_message = "user message"

    stock_ticker_result = await stock_ticker_service.get_stock_tickers(
        assistant_message, user_message
    )

    assert stock_ticker_result.success is False
    assert stock_ticker_result.response is None


@pytest.mark.asyncio
async def test_get_stock_tickers_none_response(stock_ticker_service, mock_llm_service):
    mock_llm_service.complete_async.return_value = AsyncMock(
        choices=[MagicMock(message=MagicMock(content=None))]
    )

    assistant_message = "assistant message"
    user_message = "user message"

    stock_ticker_result = await stock_ticker_service.get_stock_tickers(
        assistant_message, user_message
    )

    assert stock_ticker_result.success is False
    assert stock_ticker_result.response is None


@pytest.mark.asyncio
async def test_append_stock_diagram_to_assistant_message(
    stock_ticker_service, mock_chat_service
):
    assistant_message = "assistant message"
    diagram = "diagram"

    result = await stock_ticker_service.append_stock_diagram_to_message(
        assistant_message, diagram
    )

    expected_content = f"{assistant_message}\n\n{diagram}\n\n"
    assert result == expected_content
