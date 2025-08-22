from unique_stock_ticker.clients.six.schema import (
    BaseRequestParams,
    MarketType,
)


class FreeTextSearchMarketsRequestParams(BaseRequestParams):
    text: str
    size: int | None = 10
    market_type: MarketType | None = None
