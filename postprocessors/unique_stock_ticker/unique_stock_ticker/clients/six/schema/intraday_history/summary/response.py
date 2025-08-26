from datetime import datetime

from pydantic import Field

from unique_stock_ticker.clients.six.schema import (
    BaseAPIModel,
    BaseResponsePayload,
    ListingIdentifierScheme,
    ListingStatus,
    LookupStatus,
)


class IntradayHistorySummaryItem(BaseAPIModel):
    interval_from: datetime | None = Field(
        default=None,
        description="Date and time in ISO-8601 when the interval starts.",
    )
    interval_to: datetime | None = Field(
        default=None,
        description="Date and time in ISO-8601 when the interval ends.",
    )
    number_of_trades: int | None = Field(
        default=None, description="The number of trades per interval."
    )
    open: float | None = Field(
        default=None,
        description="An Open is associated with the first transaction of the day. It follows immediately after the opening auction (if any) is completed. It is an opening price or first recorded price of the trading day - any value that the provider officially designates as the open. It is not necessarily a transacted price.",
    )
    high: float | None = Field(
        default=None,
        description="A High is the highest traded price for the security within the current trading session. If not delivered by the price information provider and there is no recorded trade price, it may be computed using the highest ask of the trading session. The price can be adjusted according to corporate action events historically and dividend-adjusted.",
    )
    low: float | None = Field(
        default=None,
        description="A Low is the lowest traded price for the security within the current trading session. If not delivered by the price information provider and there is no recorded trade price, it may be computed using the lowest bid of the trading session. The price can be adjusted according to corporate action events historically.",
    )
    last: float | None = Field(
        default=None,
        description="A Last is the most recent price which, after a successful matching of buy and sell orders, is eligible to update the last trade. The Last Trade is required so that market participants can see the trade prices and estimate the impact of their order and the probability of getting the order fully executed.\n\nFurthermore, trades are required for valuation purposes, understanding if an order was executed, understanding the change in the value of a security over time, understanding liquidity and the speed of trading.",
    )
    volume: float | None = Field(
        default=None,
        description="Volume is the volume on market which is a number of units/nominal/contracts traded on market during a session. It is mainly used for analytical purposes and can be used for time series and historical data or data studies to compare it with the associated price action.",
    )


class IntradayHistorySummaryLookup(BaseAPIModel):
    listing_short_name: str = Field(
        ..., description="Listing short name with up to 19 characters."
    )
    market_short_name: str = Field(
        ...,
        description="The market short name where the instrument is listed with up to 19 characters.",
    )
    listing_currency: str = Field(
        ...,
        description="The trading currency, as specified by SIX, typically follows the ISO 4217 alpha-3 code. This is shown in the main currency and not in fractional units. For cryptocurrencies, the Cryptocurrency Symbol in Instrument Symbology can be used for reference.",
    )
    listing_status: ListingStatus = Field(
        ...,
        description="This shows the instruments status on the market - it shows if it is listed, suspended, admited to trading, delisted, etc",
    )


class IntradayHistorySummaryHistory(BaseAPIModel):
    summary: list[IntradayHistorySummaryItem] | None = Field(
        default=None,
        description='With IntradayHistorySummary you may request aggregated price and trading activity for a specific period, with fields: open, high, low, last, volume and number of trades. The time series is delivered backwards from the "dateTo". The following considerations apply:\n\n| Period            | Max. Duration Per Request | Historical Depth  | Max. Records Per Request | Default records per request   |\n|:-----------------:|:-------------------------:|:-----------------:|:------------------------:|:-----------------------------:|\n|1 sec <= x < 5 min | 2 days                    | 10 days           | 20000                    | 1600*                         |\n|5 min <= x <= 60min| 30 days                   | 90 days           | 20000                    | 1600*                         |\n\n*default records per request are only applied if no "dateFrom" has been defined.',
    )


class IntradayHistorySummaryMarketData(BaseAPIModel):
    intraday_history: IntradayHistorySummaryHistory | None = None


class IntradayHistorySummaryListingsItem(BaseAPIModel):
    requested_id: str = Field(
        ..., description="The requested entity id used in the request"
    )
    requested_scheme: ListingIdentifierScheme = Field(
        ..., description="The requested scheme used in the request"
    )
    lookup_status: LookupStatus = Field(..., description="Status of the response")
    lookup: IntradayHistorySummaryLookup | None = None
    market_data: IntradayHistorySummaryMarketData | None = None


class IntradayHistorySummaryListingsData(BaseAPIModel):
    listings: list[IntradayHistorySummaryListingsItem] | None = None


class IntradayHistorySummaryResponsePayload(BaseResponsePayload):
    data: IntradayHistorySummaryListingsData | None = None
