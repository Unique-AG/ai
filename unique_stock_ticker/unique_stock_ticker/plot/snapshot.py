import datetime
from logging import getLogger

from unique_stock_ticker.clients.six.client import SixApiClient
from unique_stock_ticker.clients.six.exception import raise_errors_from_api_response
from unique_stock_ticker.clients.six.schema.common.listing import (
    ListingIdentifierScheme,
)
from unique_stock_ticker.clients.six.schema.intraday_snapshot.response import (
    IntradaySnapshotResponsePayload,
    IntradaySnapshotValues,
)
from unique_stock_ticker.plot.backend.base.schema import MetricName


def _check_response_data(
    resp: IntradaySnapshotResponsePayload,
) -> bool:
    return resp.data is not None and resp.data.listings is not None


logger = getLogger(__name__)


def extract_metrics_from_snapshot(
    snapshot: IntradaySnapshotValues,
    field_to_name: dict[str, MetricName] | None = None,
) -> dict[MetricName, tuple[float, datetime.datetime]]:
    if field_to_name is None:
        field_to_name = {
            "open": MetricName.OPEN,
            "high": MetricName.HIGH,
            "close": MetricName.CLOSE,
            "market_capitalisation": MetricName.MARKET_CAP,
            "price_earnings_ratio_reported": MetricName.PRICE_EARNINGS_RATIO,
            "volume": MetricName.VOLUME,
            "high_year_to_date": MetricName.YEAR_HIGH,
            "low_year_to_date": MetricName.YEAR_LOW,
            "dividend_yield": MetricName.DIVIDEND_YIELD,
            "historical_volatility30_days": MetricName.VOLATILITY_30_DAYS,
        }

    metrics = {}
    for field, name in field_to_name.items():
        metric = getattr(snapshot, field)
        if metric is not None:
            metrics[name] = (metric.value, metric.timestamp)
    return metrics


async def get_snapshot_information_for_listings(
    client: SixApiClient,
    scheme: ListingIdentifierScheme,
    ids: list[str],
) -> list[IntradaySnapshotValues | None]:
    logger.info("Getting snapshot information for listings %s", ids)

    resp = client.intraday_snapshot(
        scheme=scheme,
        ids=",".join(ids),
    )
    raise_errors_from_api_response(resp)

    if not _check_response_data(resp):
        logger.error("Error retrieving snapshot information")
        return [None] * len(ids)

    value_by_id = {}
    for listing in resp.data.listings:  # type: ignore
        if listing.market_data is None or listing.market_data.intraday_snapshot is None:
            logger.warning(
                "No snapshot information found for listing %s",
                listing.requested_id,
            )
            continue
        value_by_id[listing.requested_id] = listing.market_data.intraday_snapshot

    ordered_res = []
    for id in ids:
        if id not in value_by_id:
            logger.warning("No snapshot information found for listing %s", id)
            ordered_res.append(None)
        else:
            ordered_res.append(value_by_id[id])

    return ordered_res
