import asyncio
import logging
from datetime import date, timedelta

from unique_six.client import SixApiClient
from unique_six.schema.common.instrument import InstrumentType
from unique_six.schema.common.listing import (
    ListingIdentifierScheme,
)
from unique_six.schema.end_of_day_history.response import (
    EndOfDayHistoryItem,
)
from unique_six.schema.entity_base.listing.response import (
    EntityBaseByListingEntityBase,
)
from unique_six.schema.free_text_search.instruments.response import (
    FreeTextInstrumentSearchHit,
)
from unique_six.schema.intraday_history.summary.response import (
    IntradayHistorySummaryItem,
)
from unique_six.schema.intraday_snapshot.response import (
    IntradaySnapshotValues,
)
from unique_toolkit._common.execution import (
    SafeTaskExecutor,
    safe_execute_async,
)

from unique_stock_ticker.plot.backend.base.base import PlottingBackend
from unique_stock_ticker.plot.backend.base.schema import (
    PriceHistoryItem,
    StockHistoryPlotPayload,
    StockInfo,
    StockMetric,
)
from unique_stock_ticker.plot.entity import get_entity_info_for_listings
from unique_stock_ticker.plot.history import (
    get_pricing_history_for_listings_with_period,
    get_pricing_history_general,
    should_use_intraday_history_endpoint,
)
from unique_stock_ticker.plot.snapshot import (
    extract_metrics_from_snapshot,
    get_snapshot_information_for_listings,
)
from unique_stock_ticker.plot.ticker import find_instrument_from_ticker

logger = logging.getLogger(__name__)


async def _par_free_text_instrument_search(
    client: SixApiClient,
    tickers: list[str],
    instrument_types: list[InstrumentType],
    search_size: int = 5,
) -> list[FreeTextInstrumentSearchHit | None]:
    task_executor = SafeTaskExecutor(logger=logger)

    tasks = []
    for ticker, instrument_type in zip(tickers, instrument_types):
        tasks.append(
            task_executor.execute_async(
                find_instrument_from_ticker,
                client=client,
                ticker=ticker,
                search_size=search_size,
                instrument_type=instrument_type,
            )
        )

    task_results = await asyncio.gather(*tasks)

    res = [task_result.unpack(None) for task_result in task_results]

    return res


def _extract_price_data_from_datapoint(
    datapoint: IntradayHistorySummaryItem | EndOfDayHistoryItem,
) -> PriceHistoryItem | None:
    match datapoint:
        case IntradayHistorySummaryItem():
            if datapoint.last is None or datapoint.interval_from is None:
                return None
            return PriceHistoryItem(
                date=datapoint.interval_from,
                value=datapoint.last,
            )
        case EndOfDayHistoryItem():
            if datapoint.close is None:
                return None
            return PriceHistoryItem(
                date=datapoint.session_date,
                value=datapoint.close,
            )
        case _:
            return None


def _extract_last_datapoint_per_day(
    price_history: list[IntradayHistorySummaryItem],
) -> list[IntradayHistorySummaryItem]:
    max_date_datapoint_per_day = {}
    for price in price_history:
        time = price.interval_from

        if time is not None:
            max_date_datapoint_per_day[time.date()] = price

    return list(max_date_datapoint_per_day.values())


async def _complete_missing_days_prices_with_intraday_endpoint(
    client: SixApiClient,
    scheme: ListingIdentifierScheme,
    ids: list[str],
    price_history: list[list[EndOfDayHistoryItem] | None],
) -> list[list[IntradayHistorySummaryItem] | None]:
    logger.info("Completing missing days data for instruments %s", ids)

    max_retrieved_date_per_ticker = []
    start_date_for_request = date.today()
    for history in price_history:
        if history is None:
            max_retrieved_date_per_ticker.append(None)
            continue

        if len(history) > 0:
            max_retrieved_date = max(price.session_date for price in history)
            max_retrieved_date_per_ticker.append(max_retrieved_date)
            start_date_for_request = min(start_date_for_request, max_retrieved_date)
        else:
            max_retrieved_date_per_ticker.append(None)

    if start_date_for_request == date.today():
        logger.info("Data is up to date until today")
        return [None] * len(price_history)

    intraday_snapshot_values = await safe_execute_async(
        get_pricing_history_for_listings_with_period,
        client=client,
        scheme=scheme,
        ids=ids,
        start_date=start_date_for_request,
        period=timedelta(hours=1),  # max timedelta
    )

    if not intraday_snapshot_values.success:
        logger.error("Could not retrieve missing data using intraday history endpoint")
        return [None] * len(price_history)

    intraday_snapshot_values = intraday_snapshot_values.unpack()

    added_datapoints = []
    for index, extra_values in enumerate(intraday_snapshot_values):
        max_date_for_ticker = max_retrieved_date_per_ticker[index]
        if extra_values is None or max_date_for_ticker is None:
            added_datapoints.append(None)
            continue

        extra_values = list(
            filter(
                lambda x: x is not None
                and x.interval_from is not None
                and (
                    max_date_for_ticker is None
                    or x.interval_from.date() > max_date_for_ticker
                ),
                extra_values,
            )
        )

        if len(extra_values) == 0:
            logger.info("No available extra data for instrument %s", ids[index])
            added_datapoints.append(None)
            continue

        added_datapoints.append(_extract_last_datapoint_per_day(extra_values))

    return added_datapoints


async def _par_get_data_for_plots(
    client: SixApiClient,
    scheme: ListingIdentifierScheme,
    ids: list[str],
    start_date: date,
    end_date: date | None = None,
    period: timedelta | None = None,
) -> list[
    tuple[
        list[IntradayHistorySummaryItem | EndOfDayHistoryItem],
        IntradaySnapshotValues | None,
        EntityBaseByListingEntityBase,
    ]
    | None
]:
    async with asyncio.TaskGroup() as tg:
        use_intraday_history_endpoint = should_use_intraday_history_endpoint(
            start_date, end_date
        )

        # 1. Get pricing history
        pricing_history = tg.create_task(
            get_pricing_history_general(
                client,
                scheme,
                ids,
                start_date,
                end_date,
                period,
                use_intraday_history_endpoint,
            ),
        )

        # 2. Get snapshot information
        snapshot_information = tg.create_task(
            safe_execute_async(
                get_snapshot_information_for_listings,
                client,
                scheme,
                ids,
            ),
        )  # OK if this fails, we won't display any metrics

        # 3. Get company info
        entity_info = tg.create_task(
            get_entity_info_for_listings(client, scheme, ids),
        )

    pricing_history = pricing_history.result()

    snapshot_information = snapshot_information.result().unpack(
        [None] * len(pricing_history)  # type: ignore
    )
    entity_info = entity_info.result()

    if not use_intraday_history_endpoint:
        extra_data = await _complete_missing_days_prices_with_intraday_endpoint(
            client=client,
            scheme=scheme,
            ids=ids,
            price_history=pricing_history,  # type: ignore
        )
        for history, extra_data_for_instrument in zip(pricing_history, extra_data):
            if history is None or extra_data_for_instrument is None:
                continue
            history.extend(extra_data_for_instrument)  # type: ignore

    res = []

    for i in range(len(pricing_history)):
        history, snapshot, entity = (
            pricing_history[i],
            snapshot_information[i],
            entity_info[i],
        )
        if history is None or entity is None:
            res.append(None)  # We fail here since frontend doesn't expect nulls
        else:
            res.append((history, snapshot, entity))

    return res


async def find_history_for_tickers(
    client: SixApiClient,
    tickers: list[str],
    instrument_types: list[InstrumentType],
    start_date: date,
    end_date: date | None = None,
    search_size: int = 5,
    period: timedelta | None = None,
) -> list[StockHistoryPlotPayload]:
    valid_tickers_search_info = []
    valid_tickers = []

    # 1. Find instrument info
    free_text_search_info = await _par_free_text_instrument_search(
        client,
        tickers,
        instrument_types=instrument_types,
        search_size=search_size,
    )
    for ticker, info in zip(tickers, free_text_search_info):
        if info is None:
            continue
        valid_tickers_search_info.append(info)
        valid_tickers.append(ticker)

    if len(valid_tickers) == 0:
        return []

    # 2. Get plotting data
    valor_bc_ids = [
        f"{info.valor}_{info.most_liquid_market.bc}"  # type: ignore
        for info in valid_tickers_search_info
    ]
    plotting_data = await _par_get_data_for_plots(
        client=client,
        scheme=ListingIdentifierScheme.VALOR_BC,
        ids=valor_bc_ids,
        start_date=start_date,
        end_date=end_date,
        period=period,
    )

    # 3. Prepare payload for plotting backend
    payload = []
    for ticker, ticker_data, search_info in zip(
        valid_tickers, plotting_data, valid_tickers_search_info
    ):
        logger.debug("Preparing plotting data for ticker: %s", ticker)
        if ticker_data is None:
            logger.debug("No data for ticker: %s", ticker)
            continue

        pricing_history, snapshot_information, entity_info = ticker_data
        if len(pricing_history) == 0:
            logger.debug("No pricing history for ticker: %s", ticker)
            continue

        if entity_info.entity_short_name is None:
            logger.debug("No entity info for ticker: %s", ticker)
            continue

        stock_info_payload = StockInfo(
            company_name=entity_info.entity_short_name,
            ticker=ticker,
            exchange=search_info.most_liquid_market.short_name,
            currency=search_info.nominal_currency,
            instrument_name=search_info.instrument_short_name,
        )

        history_payload = []
        for session in pricing_history:
            price_item = _extract_price_data_from_datapoint(session)
            if price_item is None:
                continue
            history_payload.append(price_item)

        metrics_payload = []
        if snapshot_information is not None:
            metrics_payload = [
                StockMetric(
                    name=metric_name,
                    value=metric_value,
                    timestamp=metric_timestamp,
                )
                for metric_name, (
                    metric_value,
                    metric_timestamp,
                ) in extract_metrics_from_snapshot(snapshot_information).items()
            ]

        payload.append(
            StockHistoryPlotPayload(
                info=stock_info_payload,
                price_history=history_payload,
                metrics=metrics_payload,
            )
        )
    return payload


async def find_and_plot_history_for_tickers(
    client: SixApiClient,
    plotting_backend: PlottingBackend,
    tickers: list[str],
    instrument_types: list[InstrumentType],
    start_date: date,
    end_date: date | None = None,
    search_size: int = 5,
    period: timedelta | None = None,
) -> str:
    payload = await find_history_for_tickers(
        client=client,
        tickers=tickers,
        instrument_types=instrument_types,
        start_date=start_date,
        end_date=end_date,
        search_size=search_size,
        period=period,
    )
    return plotting_backend.plot(payload)
