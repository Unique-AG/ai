from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel
from unique_toolkit.agentic.tools.config import get_configuration_dict

from unique_stock_ticker.plot.backend.base.schema import (
    StockHistoryPlotPayload,
)


class PlottingBackendName(StrEnum):
    PLOTLY = "plotly"
    NEXT = "next"


T = TypeVar("T", bound=PlottingBackendName)


class PlottingBackendConfig(BaseModel, Generic[T]):
    model_config = get_configuration_dict()
    name: T


ConfigType = TypeVar("ConfigType", bound=PlottingBackendConfig)


class PlottingBackend(ABC, Generic[ConfigType]):
    def __init__(self, config: ConfigType):
        self.config = config

    @abstractmethod
    def plot(
        self,
        ticker_data: list[StockHistoryPlotPayload],
    ) -> str:
        """This function should return plotting Result to be be appended to the chat message."""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def remove_result_from_text(cls, text: str) -> str:
        """This function should remove the result of `plot` from the text."""
        raise NotImplementedError
