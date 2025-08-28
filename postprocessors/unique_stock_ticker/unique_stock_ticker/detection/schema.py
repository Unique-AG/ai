from pydantic import BaseModel, Field
from typing_extensions import Literal


class StockTicker(BaseModel):
    explanation: str = Field(
        description="Describe in one sentence why the ticker was chosen in the case where a company may have multiple tickers",
        examples=[
            "BAYN was chosen for Bayer AG as it is the ticker for the Frankfurt stock exchange, where most Bayer AG shares are traded"
        ],
    )
    ticker: str = Field(
        description="Ticker for the given stock",
        examples=["AAPL", "GOOG", "BAYN"],
    )
    company_name: str = Field(
        description="Name of the company or ETF",
        examples=["Apple", "Google", "Bayer"],
    )
    instrument_type: Literal["equity", "etf"] = Field(
        description="Type of instrument",
    )


class StockTickerList(BaseModel):
    tickers: list[StockTicker]


class getStockTickersResponse(BaseModel):
    success: bool
    response: list[StockTicker] | None = None
