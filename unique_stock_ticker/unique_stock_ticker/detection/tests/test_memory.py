from unittest.mock import MagicMock

import pytest
from unique_toolkit.short_term_memory.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)

from unique_stock_ticker.detection.memory import (
    StockTickerMemoryConfig,
    StockTickerMemoryManager,
    StockTickerMemorySchema,
)
from unique_stock_ticker.detection.schema import StockTicker


class TestStockTickerMemorySchema:
    def test_increment(self):
        """Test that increment increases all counter values by 1"""
        schema = StockTickerMemorySchema(ticker_counter={"AAPL": 1, "MSFT": 2})
        result = schema.increment()

        assert result.ticker_counter["AAPL"] == 2
        assert result.ticker_counter["MSFT"] == 3
        assert result is schema, "Method should return self"

    def test_remove_outdated(self):
        """Test that remove_outdated removes tickers with counts above max_counter"""
        schema = StockTickerMemorySchema(
            ticker_counter={"AAPL": 1, "MSFT": 3, "GOOG": 5}
        )
        result = schema.remove_outdated(max_counter=3)

        assert "AAPL" in result.ticker_counter
        assert "MSFT" in result.ticker_counter
        assert "GOOG" not in result.ticker_counter
        assert result is schema, "Method should return self"

    def test_add(self):
        """Test that add inserts new tickers with counter set to 0"""
        schema = StockTickerMemorySchema(ticker_counter={"AAPL": 1})
        result = schema.add("MSFT", "GOOG")

        assert result.ticker_counter["AAPL"] == 1, "Existing ticker should be unchanged"
        assert result.ticker_counter["MSFT"] == 0, (
            "New ticker should be initialized to 0"
        )
        assert result.ticker_counter["GOOG"] == 0, (
            "New ticker should be initialized to 0"
        )
        assert result is schema, "Method should return self"

        # Test adding existing ticker doesn't change its value
        schema.add("AAPL")
        assert schema.ticker_counter["AAPL"] == 1, (
            "Re-adding existing ticker shouldn't change its value"
        )


@pytest.fixture
def memory_manager():
    return MagicMock(spec=PersistentShortMemoryManager)


@pytest.fixture
def ticker_manager(memory_manager):
    config = StockTickerMemoryConfig(max_chat_interactions=3)
    return StockTickerMemoryManager(
        config=config,
        memory_manager=memory_manager,
    )


class TestStockTickerMemoryManager:
    def test_process_new_tickers_empty_memory(self, ticker_manager, memory_manager):
        """Test processing tickers when memory is empty"""
        # Setup memory manager to return None (empty memory)
        memory_manager.load_sync.return_value = None

        # Create test tickers
        tickers = [
            StockTicker(
                ticker="AAPL",
                company_name="Apple Inc.",
                explanation="",
                instrument_type="equity",
            ),
            StockTicker(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                explanation="",
                instrument_type="equity",
            ),
        ]

        # Process tickers
        result = ticker_manager.process_new_tickers(tickers)

        # Verify all tickers are considered new
        assert len(result) == 2
        assert result[0].ticker == "AAPL"
        assert result[0].company_name == "Apple Inc."
        assert result[0].explanation == ""
        assert result[1].ticker == "MSFT"
        assert result[1].company_name == "Microsoft Corporation"
        assert result[1].explanation == ""

        # Verify memory was saved with the new tickers
        memory_manager.save_sync.assert_called_once()
        saved_memory = memory_manager.save_sync.call_args[0][0]
        assert "AAPL" in saved_memory.ticker_counter
        assert "MSFT" in saved_memory.ticker_counter
        assert saved_memory.ticker_counter["AAPL"] == 0
        assert saved_memory.ticker_counter["MSFT"] == 0

    def test_process_new_tickers_with_existing_memory(
        self, ticker_manager, memory_manager
    ):
        """Test processing tickers when some are already in memory"""
        # Setup memory with existing ticker
        existing_memory = StockTickerMemorySchema(ticker_counter={"AAPL": 1})
        memory_manager.load_sync.return_value = existing_memory

        # Create test tickers
        tickers = [
            StockTicker(
                ticker="AAPL",
                company_name="Apple Inc.",
                explanation="",
                instrument_type="equity",
            ),
            StockTicker(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                explanation="",
                instrument_type="equity",
            ),
        ]

        # Process tickers
        result = ticker_manager.process_new_tickers(tickers)

        # Verify only MSFT is considered new
        assert len(result) == 1
        assert result[0].ticker == "MSFT"
        assert result[0].company_name == "Microsoft Corporation"
        assert result[0].explanation == ""

        # Verify memory was updated correctly
        memory_manager.save_sync.assert_called_once()
        saved_memory = memory_manager.save_sync.call_args[0][0]
        assert "AAPL" in saved_memory.ticker_counter
        assert "MSFT" in saved_memory.ticker_counter
        assert saved_memory.ticker_counter["AAPL"] == 2  # Incremented
        assert saved_memory.ticker_counter["MSFT"] == 0  # New

    def test_process_new_tickers_removes_outdated(self, ticker_manager, memory_manager):
        """Test that outdated tickers are removed during processing"""
        # Setup memory with tickers at different counter values
        existing_memory = StockTickerMemorySchema(
            ticker_counter={"AAPL": 1, "GOOG": 2, "AMZN": 3}
        )
        memory_manager.load_sync.return_value = existing_memory

        # Create test tickers
        tickers = [
            StockTicker(
                ticker="AAPL",
                company_name="Apple Inc.",
                explanation="",
                instrument_type="equity",
            ),
            StockTicker(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                explanation="",
                instrument_type="equity",
            ),
        ]

        # Process tickers
        result = ticker_manager.process_new_tickers(tickers)

        # Verify only MSFT is considered new
        assert len(result) == 1
        assert result[0].ticker == "MSFT"
        assert result[0].company_name == "Microsoft Corporation"
        assert result[0].explanation == ""

        # Verify memory was updated correctly
        saved_memory = memory_manager.save_sync.call_args[0][0]
        assert "AAPL" in saved_memory.ticker_counter
        assert "GOOG" in saved_memory.ticker_counter
        assert (
            "AMZN" not in saved_memory.ticker_counter
        )  # Removed (exceeded max_counter)
        assert "MSFT" in saved_memory.ticker_counter
        assert saved_memory.ticker_counter["AAPL"] == 2  # Incremented
        assert saved_memory.ticker_counter["GOOG"] == 3  # Incremented, at max
        assert saved_memory.ticker_counter["MSFT"] == 0  # New

    def test_process_empty_tickers_list(self, ticker_manager, memory_manager):
        """Test processing an empty list of tickers"""
        # Setup memory with existing ticker
        existing_memory = StockTickerMemorySchema(ticker_counter={"AAPL": 1})
        memory_manager.load_sync.return_value = existing_memory

        # Process empty list
        result = ticker_manager.process_new_tickers([])

        # Verify result is empty
        assert len(result) == 0

        # Verify memory was still updated (incremented)
        saved_memory = memory_manager.save_sync.call_args[0][0]
        assert saved_memory.ticker_counter["AAPL"] == 2  # Incremented

    def test_custom_max_chat_interactions(self, memory_manager):
        """Test with a custom max_chat_interactions value"""
        # Create manager with custom config
        custom_config = StockTickerMemoryConfig(max_chat_interactions=1)
        custom_manager = StockTickerMemoryManager(
            config=custom_config,
            memory_manager=memory_manager,
        )

        # Setup memory with tickers at different counter values
        existing_memory = StockTickerMemorySchema(ticker_counter={"AAPL": 1, "GOOG": 2})
        memory_manager.load_sync.return_value = existing_memory

        # Process tickers
        tickers = [
            StockTicker(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                explanation="",
                instrument_type="equity",
            )
        ]
        custom_manager.process_new_tickers(tickers)

        # Verify memory was updated correctly
        saved_memory = memory_manager.save_sync.call_args[0][0]
        assert "MSFT" in saved_memory.ticker_counter  # New

        # Check that tickers exceeding max_chat_interactions were removed
        # AAPL incremented to 2, GOOG incremented to 3, both exceed max of 1
        assert "AAPL" not in saved_memory.ticker_counter
        assert "GOOG" not in saved_memory.ticker_counter


@pytest.mark.parametrize(
    "initial_counter,expected_counter",
    [
        ({"AAPL": 0, "MSFT": 1}, {"AAPL": 1, "MSFT": 2}),
        ({}, {}),
        ({"GOOG": 5}, {"GOOG": 6}),
    ],
)
def test_increment_parametrized(initial_counter, expected_counter):
    """Test increment with various initial states"""
    schema = StockTickerMemorySchema(ticker_counter=initial_counter)
    schema.increment()
    assert schema.ticker_counter == expected_counter


@pytest.mark.parametrize(
    "initial_counter,max_counter,expected_counter",
    [
        ({"AAPL": 1, "MSFT": 3, "GOOG": 5}, 3, {"AAPL": 1, "MSFT": 3}),
        ({"AAPL": 1, "MSFT": 2}, 5, {"AAPL": 1, "MSFT": 2}),
        ({}, 3, {}),
        ({"AAPL": 10, "MSFT": 20}, 5, {}),
    ],
)
def test_remove_outdated_parametrized(initial_counter, max_counter, expected_counter):
    """Test remove_outdated with various initial states and max values"""
    schema = StockTickerMemorySchema(ticker_counter=initial_counter)
    schema.remove_outdated(max_counter)
    assert schema.ticker_counter == expected_counter
