from unique_six.schema import (
    BaseRequestParams,
    MarketType,
)


class FreeTextSearchMarketsRequestParams(BaseRequestParams):
    text: str
    size: int | None = 10
    market_type: MarketType | None = None
