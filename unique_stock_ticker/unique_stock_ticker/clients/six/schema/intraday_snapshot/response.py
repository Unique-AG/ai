from datetime import datetime

from pydantic import Field

from unique_stock_ticker.clients.six.schema import (
    BaseAPIModel,
    BaseResponsePayload,
    ListingIdentifierScheme,
    ListingStatus,
    LookupStatus,
)
from unique_stock_ticker.clients.six.schema.intraday_snapshot.quality_of_service import (
    QualityOfService,
)


class SixAPISnapshotValue(BaseAPIModel):
    value: float | None = Field(
        default=None, description="The Value of the price type."
    )
    timestamp: datetime = Field(
        ...,
        description="Generally, in real-time feeds, the providers disseminate various Timestamps that are associated with different price types or events. There could be multiple timestamps associated with a given price.\n\nDifferent providers may have different names for these timestamps and will not necessarily provide all of them in their feeds. In some cases, if the timestamp is not provided by the exchange, SIX internal timestamp may be used.\n\nIn SIX products only one timestamp can be displayed with a given price or event. If the exchange provides multiple timestamps within the feed, use the timestamps in the following priority:\n\nMarket data entry time - the time when the price was entered on a trader's side.\nTransaction time - the time when the price was recognized by the exchange.\nExchange processing time - the time when the price was processed for updates, calculations at the exchange.\nExchange's sending time - the time that the exchange disseminate the price via the feed.",
    )


class SixAPISnapshotValueWithSize(SixAPISnapshotValue):
    size: float | None = Field(
        default=None,
        description="A Size associated with a price value represent an amount of units/contracts/nominal offered for sale, demanded for purchase, traded, orders that will be executed at a given price (e.g. in the event of an auction theoretical matching price quantity).\n\nThe size associated with a quote can directly signal the market participant the ability of the market to absorb their order. Furthermore, it provides an indication of a market imbalance. The Ask Size is required by traders trading data products and those entities interest in intra-day market data values.\n\nThe size associated with a trade allows a market participant to see the trade volumes and estimate or understand the impact of their own order on the market and the probability of getting it fully executed. In addition, the trade size allows calculation of the Volume Weighted Average Price (VWAP).",
    )


class SixAPISnapshotValueWithUnixTimestamp(SixAPISnapshotValue):
    unix_timestamp: float = Field(
        ...,
        description="Same as `timestamp`, but represented as IEEE 754 float: numberOfSeconds.microSeconds. Timezone is always UTC.",
    )


class IntradaySnapshotLookup(BaseAPIModel):
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


class IntradaySnapshotValues(BaseAPIModel):
    quality_of_service: QualityOfService | None = Field(
        default=None,
        description="The up-to-dateness of price data, also referred to as 'Data Quality Timeliness' or 'License Quality', is determined by the default priority when no specific quality is chosen by the client in their request.\nThe available quality levels are delivered based on the following order:\n1. REAL_TIME\n2. DELAYED\n3. END_OF_DAY\n4. PREVIOUS_DAY",
    )
    open: SixAPISnapshotValueWithSize | None = None
    high: SixAPISnapshotValue | None = None
    low: SixAPISnapshotValueWithSize | None = None
    close: SixAPISnapshotValueWithSize | None = None
    last: SixAPISnapshotValue | None = None
    reported_price: SixAPISnapshotValueWithSize | None = None
    best_ask: SixAPISnapshotValueWithSize | None = None
    best_bid: SixAPISnapshotValueWithSize | None = None
    spread_best_bid_ask: SixAPISnapshotValue | None = None
    percentage_spread_best_bid_ask: SixAPISnapshotValue | None = None
    mid: SixAPISnapshotValue | None = None
    number_of_trades: SixAPISnapshotValue | None = None
    auction_theoretical_matching_price: SixAPISnapshotValue | None = None
    open_interest: SixAPISnapshotValue | None = None
    settlement_price: SixAPISnapshotValue | None = None
    high52_week: SixAPISnapshotValue | None = None
    low52_week: SixAPISnapshotValue | None = None
    yield_to_maturity: SixAPISnapshotValue | None = None
    dividend_yield: SixAPISnapshotValue | None = None
    market_capitalisation: SixAPISnapshotValue | None = None
    volume: SixAPISnapshotValue | None = None
    volume_total: SixAPISnapshotValue | None = None
    turnover: SixAPISnapshotValue | None = None
    turnover_total: SixAPISnapshotValue | None = None
    net_change_last: SixAPISnapshotValue | None = None
    percentage_change_last: SixAPISnapshotValue | None = None
    net_change_reported_price: SixAPISnapshotValueWithUnixTimestamp | None = None
    percentage_change_reported_price: SixAPISnapshotValueWithUnixTimestamp | None = None
    price_earnings_ratio_reported: SixAPISnapshotValue | None = None
    price_earnings_ratio_estimated: SixAPISnapshotValue | None = None
    delta: SixAPISnapshotValue | None = None
    vega: SixAPISnapshotValue | None = None
    gamma: SixAPISnapshotValue | None = None
    theta: SixAPISnapshotValue | None = None
    rho: SixAPISnapshotValue | None = None
    omega: SixAPISnapshotValue | None = None
    gearing: SixAPISnapshotValue | None = None
    moneyness: SixAPISnapshotValue | None = None
    break_even_point: SixAPISnapshotValue | None = None
    intrinsic_value: SixAPISnapshotValue | None = None
    implied_volatility: SixAPISnapshotValue | None = None
    historical_volatility30_days: SixAPISnapshotValue | None = None
    historical_volatility90_days: SixAPISnapshotValue | None = None
    historical_volatility180_days: SixAPISnapshotValue | None = None
    historical_volatility250_days: SixAPISnapshotValue | None = None
    high_year_to_date: SixAPISnapshotValue | None = None
    low_year_to_date: SixAPISnapshotValue | None = None
    high_static_limit: SixAPISnapshotValue | None = None
    low_static_limit: SixAPISnapshotValue | None = None
    high1_week: SixAPISnapshotValue | None = None
    low1_week: SixAPISnapshotValue | None = None
    high4_week: SixAPISnapshotValue | None = None
    low4_week: SixAPISnapshotValue | None = None
    high12_week: SixAPISnapshotValue | None = None
    low12_week: SixAPISnapshotValue | None = None
    high26_week: SixAPISnapshotValue | None = None
    low26_week: SixAPISnapshotValue | None = None
    close_year: SixAPISnapshotValue | None = None
    performance_year_to_date: SixAPISnapshotValue | None = None
    percentage_change5_days: SixAPISnapshotValue | None = None
    percentage_change_year_to_date: SixAPISnapshotValue | None = None
    percentage_change1_week: SixAPISnapshotValue | None = None
    percentage_change4_week: SixAPISnapshotValue | None = None
    percentage_change12_week: SixAPISnapshotValue | None = None
    percentage_change26_week: SixAPISnapshotValue | None = None
    percentage_change52_week: SixAPISnapshotValue | None = None
    latest_dividend: SixAPISnapshotValue | None = None
    annualised_dividend: SixAPISnapshotValue | None = None
    indicated_annual_dividend: SixAPISnapshotValue | None = None
    average_daily_volume4_week: SixAPISnapshotValue | None = None
    average_daily_volume1_week: SixAPISnapshotValue | None = None
    average_daily_volume12_week: SixAPISnapshotValue | None = None
    average_daily_volume26_week: SixAPISnapshotValue | None = None
    average_daily_volume52_week: SixAPISnapshotValue | None = None
    average_daily_volume_month_to_date: SixAPISnapshotValue | None = None
    average_daily_volume_previous_month: SixAPISnapshotValue | None = None
    volume1_week: SixAPISnapshotValue | None = None
    volume4_week: SixAPISnapshotValue | None = None
    volume12_week: SixAPISnapshotValue | None = None
    volume26_week: SixAPISnapshotValue | None = None
    volume52_week: SixAPISnapshotValue | None = None
    turnover1_week: SixAPISnapshotValue | None = None
    turnover4_week: SixAPISnapshotValue | None = None
    turnover12_week: SixAPISnapshotValue | None = None
    turnover26_week: SixAPISnapshotValue | None = None
    turnover52_week: SixAPISnapshotValue | None = None
    duration: SixAPISnapshotValue | None = None
    modified_duration: SixAPISnapshotValue | None = None
    convexity: SixAPISnapshotValue | None = None
    accrued_interest: SixAPISnapshotValue | None = None
    time_to_maturity: SixAPISnapshotValue | None = None
    yield_to_call: SixAPISnapshotValue | None = None
    total_expense_ratio: SixAPISnapshotValue | None = None
    vwap: SixAPISnapshotValue | None = None


class IntradaySnapshotMarketData(BaseAPIModel):
    intraday_snapshot: IntradaySnapshotValues | None = None


class IntradaySnapshotItem(BaseAPIModel):
    requested_id: str = Field(
        ..., description="The requested entity id used in the request"
    )
    requested_scheme: ListingIdentifierScheme = Field(
        ..., description="The requested scheme used in the request"
    )
    lookup_status: LookupStatus = Field(..., description="Status of the response")
    lookup: IntradaySnapshotLookup | None = None
    market_data: IntradaySnapshotMarketData | None = None


class IntradaySnapshotData(BaseAPIModel):
    listings: list[IntradaySnapshotItem] | None = None


class IntradaySnapshotResponsePayload(BaseResponsePayload):
    data: IntradaySnapshotData | None = None
