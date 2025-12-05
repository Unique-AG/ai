import re
from datetime import datetime, timedelta
from typing import AsyncIterator

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.source_management.schema import Source

DATE_FILE_NAME_PATTERN = r"\d{2}\d{2}\d{2}"


class DateRelevancySourceIteratorConfig(BaseModel):
    model_config = get_configuration_dict()

    date_file_name_pattern: str = Field(
        default=DATE_FILE_NAME_PATTERN,
        description="The pattern to use for the date in the file name.",
    )


class DateRelevancySourceIterator:
    """This class is responsible for iterating over the sources and selecting the most relevant ones based on the date."""

    def __init__(self, config: DateRelevancySourceIteratorConfig):
        self._config = config

    async def iterate(self, *, sources: list[Source]) -> AsyncIterator[Source]:
        async def _generator() -> AsyncIterator[Source]:
            dates = [self._extract_date_from_source(source) for source in sources]
            sorted_sources = sorted(zip(sources, dates), key=lambda x: x[1])
            for source, _ in sorted_sources:
                yield source

        return _generator()

    def _extract_date_from_source(self, source: Source) -> datetime:
        match = re.search(self._config.date_file_name_pattern, source.title)
        if match:
            date_file_name = match.group(0)
            date = datetime.strptime(date_file_name, "%y%m%d")
            return date
        else:
            return datetime.now() - timedelta(days=3650)  # 10 years ago
