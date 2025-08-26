# Schema we use to communicate the plots to the frontend

import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MetricName(StrEnum):
    OPEN = "Open"
    HIGH = "High"
    CLOSE = "Close"
    MARKET_CAP = "Market Cap"
    PRICE_EARNINGS_RATIO = "Price Earnings Ratio"
    VOLUME = "Volume"
    YEAR_HIGH = "Year High"
    YEAR_LOW = "Year Low"
    DIVIDEND_YIELD = "Dividend Yield"
    VOLATILITY_30_DAYS = "Volatility 30 Days"


class DataSource(StrEnum):
    SIX = "Six"


class StockInfo(BaseModel):
    model_config = model_config
    company_name: str = Field(
        description="The name of the company corresponding to the stock.",
        examples=["Apple Inc"],
    )
    instrument_name: str = Field(
        description="The name of the instrument corresponding to the stock.",
        examples=["Apple Rg"],
    )
    ticker: str = Field(
        description="The ticker of the stock. This is the symbol used to trade the stock on the exchange.",
        examples=["AAPL", "GOOG", "MSFT"],
    )
    exchange: str = Field(
        description="The exchange where the stock is traded.",
        examples=["NASDAQ", "NYSE"],
    )
    currency: str = Field(
        description="The currency of the stock. Typically follows the ISO 4217 alpha-3 code.",
        examples=["USD", "EUR", "CHF"],
    )


class PriceHistoryItem(BaseModel):
    model_config = model_config
    date: datetime.datetime | datetime.date
    value: float


class StockMetric(BaseModel):
    model_config = model_config
    name: MetricName
    value: float
    timestamp: datetime.datetime


class StockHistoryPlotPayload(BaseModel):
    model_config = model_config
    info: StockInfo
    price_history: list[PriceHistoryItem]
    metrics: list[StockMetric]
    last_updated: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )
    data_source: DataSource = DataSource.SIX
    version: int = 1
