from typing import Self

from pydantic import BaseModel
from unique_toolkit.short_term_memory.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.short_term_memory.service import ShortTermMemoryService
from unique_toolkit.tools.config import (
    get_configuration_dict,
)

from unique_stock_ticker.detection.schema import StockTicker


class StockTickerMemorySchema(BaseModel):
    ticker_counter: dict[str, int] = {}

    def increment(self) -> Self:
        for ticker in self.ticker_counter:
            self.ticker_counter[ticker] += 1
        return self

    def remove_outdated(self, max_counter: int) -> Self:
        self.ticker_counter = {
            ticker: count
            for ticker, count in self.ticker_counter.items()
            if count <= max_counter
        }
        return self

    def add(self, *tickers: str) -> Self:
        for ticker in tickers:
            if ticker not in self.ticker_counter:
                self.ticker_counter[ticker] = 0
        return self


class StockTickerMemoryConfig(BaseModel):
    model_config = get_configuration_dict()
    max_chat_interactions: int = 3


class StockTickerMemoryManager:
    def __init__(
        self,
        config: StockTickerMemoryConfig,
        memory_manager: PersistentShortMemoryManager[StockTickerMemorySchema],
    ) -> None:
        self._max_chat_interactions = config.max_chat_interactions
        self._memory_manager = memory_manager

    def process_new_tickers(self, tickers: list[StockTicker]) -> list[StockTicker]:
        """
        Process tickers and return the list of new tickers (those not in memory)
        """

        memory = self._memory_manager.load_sync() or StockTickerMemorySchema()

        memory = memory.increment().remove_outdated(self._max_chat_interactions)

        new_tickers = []

        for ticker in tickers:
            if ticker.ticker not in memory.ticker_counter:
                new_tickers.append(ticker)
                memory.add(ticker.ticker)

        self._memory_manager.save_sync(memory)

        return new_tickers

    @classmethod
    def from_short_term_memory_service(
        cls,
        short_term_memory_service: ShortTermMemoryService,
        config: StockTickerMemoryConfig,
    ) -> Self:
        return cls(
            config=config,
            memory_manager=PersistentShortMemoryManager(
                short_term_memory_service=short_term_memory_service,
                short_term_memory_schema=StockTickerMemorySchema,
            ),
        )
