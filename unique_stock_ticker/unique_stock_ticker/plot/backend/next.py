import re
from typing import Literal

from pydantic import TypeAdapter
from typing_extensions import override

from unique_stock_ticker.plot.backend.base.base import (
    PlottingBackend,
    PlottingBackendConfig,
    PlottingBackendName,
    StockHistoryPlotPayload,
)

StockHistoryPlotPayloadList = TypeAdapter(list[StockHistoryPlotPayload])


class NextTickerPlotConfig(PlottingBackendConfig):
    name: Literal[PlottingBackendName.NEXT] = PlottingBackendName.NEXT


class NextPlottingBackend(PlottingBackend[NextTickerPlotConfig]):
    @override
    def plot(
        self,
        ticker_data: list[StockHistoryPlotPayload],
    ) -> str:
        # All we do is build a json object and return it as a string in a markdown block
        instance = StockHistoryPlotPayloadList.validate_python(ticker_data)

        if len(instance) == 0:
            return ""

        instance_str = StockHistoryPlotPayloadList.dump_json(
            instance, indent=2, by_alias=True, round_trip=True
        ).decode("utf-8")

        return f"```financialChart\n{instance_str}\n```"

    @classmethod
    @override
    def remove_result_from_text(cls, text: str) -> str:
        return re.sub(r"```financialChart[\s\S]*?```", "", text)

    @classmethod
    def extract_data_from_text(
        cls, text: str
    ) -> list[StockHistoryPlotPayload]:
        res = []
        for match in re.findall(r"```financialChart([\s\S]*?)```", text):
            res.extend(StockHistoryPlotPayloadList.validate_json(match))

        return res
