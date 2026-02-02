from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator
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

    @field_validator(
        "start_date", mode="before", json_schema_input_type=date | timedelta
    )
    @classmethod
    def handle_timedelta(cls, v: Any) -> Any:
        try:
            timeframe = TypeAdapter(timedelta).validate_python(v)
        except ValidationError:
            return v

        return date.today() + timeframe

    @field_validator("start_date", mode="after")
    @classmethod
    def check_start_date_is_in_the_past(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Start date must be in the past")
        return v
