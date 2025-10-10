from logging import getLogger

from unique_swot.services.schemas import Source

_LOGGER = getLogger(__name__)


# TODO: Implement a real earnings call collector
def collect_earnings_calls() -> list[Source]:
    _LOGGER.warning(
        "Collecting earnings calls as a data source is not implemented yet. No sources will be collected."
    )
    return []
