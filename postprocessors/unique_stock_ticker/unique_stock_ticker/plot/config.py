from datetime import date, timedelta
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    computed_field,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict


class OffSetDate(BaseModel):
    model_config = get_configuration_dict()

    anchor: Literal["today"] = Field()
    offset: timedelta = Field(default_factory=lambda: timedelta(days=0))

    @computed_field
    @property
    def date(self) -> date:
        return date.today() + self.offset


class StockTickerDataRetrievalConfig(BaseModel):
    """
    Configuration for the data retrieval of stock tickers.
    """

    model_config = get_configuration_dict()

    start_date: date | OffSetDate = Field(
        default_factory=lambda: date(date.today().year, 1, 1)  # Start of year
    )
    period: timedelta = timedelta(minutes=30)

    @property
    def effective_start_date(self) -> date:
        if isinstance(self.start_date, OffSetDate):
            return self.start_date.date
        return self.start_date

