from logging import getLogger

from unique_swot.services.schemas import Source

logger = getLogger(__name__)

# TODO: Implement a real web source collector
def collect_web_sources() -> list[Source]:
    logger.warning(
        "Collecting web sources as a data source is not implemented yet. No sources will be collected."
    )
    return []