from logging import getLogger

from unique_swot.services.schemas import Source

logger = getLogger(__name__)

# TODO: Implement a real earnings call collector
def collect_earnings_calls() -> list[Source]:
    logger.warning(
        "Collecting earnings calls as a data source is not implemented yet. No sources will be collected."
    )
    return []