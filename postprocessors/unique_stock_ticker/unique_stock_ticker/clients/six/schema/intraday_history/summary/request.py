from datetime import date, time, timedelta

from pydantic import Field

from unique_stock_ticker.clients.six.schema import (
    BaseRequestParams,
    ListingIdentifierScheme,
    PriceAdjustment,
)


class IntradayHistorySummaryRequestParams(BaseRequestParams):
    scheme: ListingIdentifierScheme
    ids: str = Field(
        ...,
        description="Listing Identifier to be provided by client as input parameter. Several identifiers can be requested comma-separated.",
    )
    date_from: date | None = None
    time_from: time | None = None
    date_to: date | None = None
    time_to: time | None = None
    price_adjustment: PriceAdjustment | None = PriceAdjustment.ADJUSTED
    period: timedelta | None = Field(
        default=timedelta(minutes=5),
        ge=timedelta(seconds=1),
        le=timedelta(minutes=60),
    )
