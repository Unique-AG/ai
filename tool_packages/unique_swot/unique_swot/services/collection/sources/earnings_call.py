from logging import getLogger

from unique_swot.services.collection.schema import Source
from unique_swot.services.collection.sources.quartr.schemas import CompanyDto

_LOGGER = getLogger(__name__)




# TODO: Implement a real earnings call collector
def collect_earnings_calls(quartr_company: CompanyDto) -> list[Source]:
    _LOGGER.warning(
        "Collecting earnings calls as a data source is not implemented yet. No sources will be collected."
    )
    return []
