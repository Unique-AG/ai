from datetime import date, timedelta
from logging import getLogger

from unique_stock_ticker.clients.six import SixApiClient, raise_errors_from_api_response
from unique_stock_ticker.clients.six.schema.common.listing import ListingIdentifierScheme
from unique_stock_ticker.clients.six.schema.end_of_day_history import (
    EndOfDayHistoryResponsePayload,
)
from unique_stock_ticker.clients.six.schema.end_of_day_history.response import (
    EndOfDayHistoryItem,
)
from unique_stock_ticker.clients.six.schema.intraday_history.summary.response import (
    IntradayHistorySummaryItem,
    IntradayHistorySummaryResponsePayload,
)

logger = getLogger(__name__)


async def get_pricing_history_for_listings_with_period(
    client: SixApiClient,
    scheme: ListingIdentifierScheme,
    ids: list[str],
    start_date: date,
    end_date: date | None = None,
    period: timedelta | None = None,
) -> list[list[IntradayHistorySummaryItem] | None]:
    logger.info(
        "Getting pricing history for listings %s from %s until %s with period %s",
        ids,
        start_date,
        end_date if end_date else "today",
        str(period),
    )

    if period is None:
        period = timedelta(minutes=5)

    resp = client.intraday_history_summary(
        scheme=scheme,
        ids=",".join(ids),
        date_from=start_date,
        date_to=end_date,
        period=period,
    )
    raise_errors_from_api_response(resp)

    if not _check_response_data(resp):
        logger.error("Error retrieving history data")
        return [None] * len(ids)

    data_by_listing = {}
    for listing in resp.data.listings:  # type: ignore
        if not (
            listing.market_data is None
            or listing.market_data.intraday_history is None
            or listing.market_data.intraday_history.summary is None
        ):
            data_by_listing[listing.requested_id] = (
                listing.market_data.intraday_history.summary
            )

    ordered_res = []

    for id in ids:
        if id not in data_by_listing:
            logger.warning("No history data found for listing %s", id)
            ordered_res.append(None)
        else:
            ordered_res.append(data_by_listing[id])

    return ordered_res


def _check_response_data(
    resp: EndOfDayHistoryResponsePayload
    | IntradayHistorySummaryResponsePayload,
) -> bool:
    return (
        resp.data is not None
        and resp.data.listings is not None
        and resp.data.listings[0].market_data is not None
    )


async def get_pricing_history_for_listings(
    client: SixApiClient,
    scheme: ListingIdentifierScheme,
    ids: list[str],
    start_date: date,
    end_date: date | None = None,
) -> list[list[EndOfDayHistoryItem] | None]:
    logger.info("Getting pricing history for listings %s", ids)

    resp = client.end_of_day_history(
        scheme=scheme,
        ids=",".join(ids),
        date_from=start_date,
        date_to=end_date,
    )
    raise_errors_from_api_response(resp)

    if not _check_response_data(resp):
        logger.error("Error retrieving history data")
        return [None] * len(ids)

    session_data_by_listing = {}
    for listing in resp.data.listings:  # type: ignore
        if listing.market_data is None:
            continue
        session_data_by_listing[listing.requested_id] = (
            listing.market_data.end_of_day_history
        )

    ordered_res = []
    for id in ids:
        if id not in session_data_by_listing:
            logger.warning("No history data found for listing %s", id)
            ordered_res.append(None)
        else:
            ordered_res.append(session_data_by_listing[id])
    return ordered_res


# We only dispatch calls to the intraday history endpoint if the number of days requested is less than this
MAX_NUM_DAYS_REQUESTED_FOR_INTRADAY_HISTORY_ENDPOINT = 30

# We only dispatch calls to the intraday history endpoint if the number of days from now is less than this
MAX_NUM_DAYS_FROM_NOW_FOR_INTRADAY_HISTORY_ENDPOINT = 90


def should_use_intraday_history_endpoint(
    start_date: date, end_date: date | None
) -> bool:
    if end_date is None:
        end_date = date.today()

    days_requested = (end_date - start_date).days + 1
    days_from_now = (date.today() - start_date).days
    return (
        days_requested <= MAX_NUM_DAYS_REQUESTED_FOR_INTRADAY_HISTORY_ENDPOINT
        and days_from_now
        <= MAX_NUM_DAYS_FROM_NOW_FOR_INTRADAY_HISTORY_ENDPOINT
    )


async def get_pricing_history_general(
    client: SixApiClient,
    scheme: ListingIdentifierScheme,
    ids: list[str],
    start_date: date,
    end_date: date | None = None,
    period: timedelta | None = None,
    use_intraday_history_endpoint: bool = False,
) -> (
    list[list[EndOfDayHistoryItem] | None]
    | list[list[IntradayHistorySummaryItem] | None]
):
    logger.debug("Start date: %s, end date: %s", start_date, end_date)
    if use_intraday_history_endpoint:
        logger.debug(
            "Using intraday history endpoint to retrieve pricing history"
        )
        return await get_pricing_history_for_listings_with_period(
            client, scheme, ids, start_date, end_date, period
        )
    else:
        logger.debug(
            "Using end of day history endpoint to retrieve pricing history"
        )
        return await get_pricing_history_for_listings(
            client, scheme, ids, start_date, end_date
        )
