from datetime import date, timedelta

from pydantic import BaseModel, Field
from unique_toolkit.agentic.tools.config import get_configuration_dict


class StockTickerDataRetrievalConfig(BaseModel):
    """
    Configuration for the data retrieval of stock tickers.
    """

    model_config = get_configuration_dict()

    start_date: date = Field(
        default_factory=lambda: date(date.today().year, 1, 1)  # Start of year
    )
    period: timedelta = timedelta(minutes=30)
