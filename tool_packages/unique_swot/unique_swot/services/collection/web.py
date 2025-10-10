from logging import getLogger

from unique_swot.services.schemas import Source

_LOGGER = getLogger(__name__)

# TODO: Implement a real web source collector
def collect_web_sources() -> list[Source]:
    _LOGGER.warning(
        "Collecting web sources as a data source is not implemented yet. No sources will be collected."
    )
    return []