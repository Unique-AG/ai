from logging import getLogger

from unique_six.client import SixApiClient
from unique_six.exception import raise_errors_from_api_response
from unique_six.schema.common.instrument import InstrumentType
from unique_six.schema.free_text_search.instruments.response import (
    FreeTextInstrumentSearchHit,
    FreeTextInstrumentSearchMostLiquidMarket,
    InstrumentMatchingDescription,
)

logger = getLogger(__name__)


def prepare_ticker(ticker: str) -> str:
    return ticker.upper().split(".")[0]


async def find_instrument_from_ticker(
    client: SixApiClient,
    ticker: str,
    search_size: int = 10,
    instrument_type: InstrumentType | None = None,
) -> FreeTextInstrumentSearchHit | None:
    """
    Find an instrument from a ticker. Can be made into a service to add caching, etc.
    """
    ticker = prepare_ticker(ticker)

    logger.info("Searching for instrument %s", ticker)

    resp = client.free_text_search_instruments(
        text=ticker, size=search_size, instrument_type=instrument_type
    )

    raise_errors_from_api_response(resp)
    if (
        resp.data is None
        or resp.data.search is None
        or resp.data.search.free_text_search is None
        or resp.data.search.free_text_search.instruments is None
        or len(resp.data.search.free_text_search.instruments) == 0
    ):
        """
        Logically these cases should not happen, but the checks are necessary due to the Open API specification.
        If this happens, we cannot recover and do not have any hints on the error.
        """
        logger.error("Error retrieving data for ticker %s", ticker)
        return None

    hits = [
        instrument
        for instrument in resp.data.search.free_text_search.instruments
        if instrument.hit is not None
        and InstrumentMatchingDescription.TICKER
        in [highlight.matching_description for highlight in instrument.highlights]
    ]

    if len(hits) == 0:
        logger.error("No instrument matches ticker %s", ticker)
        return None
    if len(hits) == 1:
        logger.debug(
            "Best match for ticker %s is %s",
            ticker,
            hits[0].hit.instrument_short_name,  # type: ignore
        )
        return hits[0].hit

    logger.warning(
        "Found %i instruments for ticker %s, using normalized score to select one",
        len(hits),
        ticker,
    )
    best_match = max(hits, key=lambda x: x.normalized_score)

    logger.debug(
        "Best match for ticker %s is %s with normalized score %s",
        ticker,
        best_match.hit.instrument_short_name,  # type: ignore
        best_match.normalized_score,
    )

    return best_match.hit


async def find_instrument_market_from_ticker(
    client: SixApiClient,
    ticker: str,
    search_size: int = 10,
    intrument_type: InstrumentType = InstrumentType.EQUITY,
) -> FreeTextInstrumentSearchMostLiquidMarket | None:
    instrument = await find_instrument_from_ticker(
        client, ticker, search_size, intrument_type
    )
    if instrument is None:
        return None
    return instrument.most_liquid_market
