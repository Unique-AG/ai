from typing import Literal

import plotly.graph_objects as go
from typing_extensions import override
from unique_toolkit.content import ContentService

from unique_stock_ticker.plot.backend.base import (
    MetricName,
    PlottingBackend,
    PlottingBackendConfig,
    PlottingBackendName,
    StockHistoryPlotPayload,
)
from unique_stock_ticker.plot.backend.plotly.functions import (
    plot_stock_price_history_plotly,
)
from unique_stock_ticker.plot.backend.plotly.save import get_image_markdown_from_content_id, save_plots_to_content_service




PlotlyTemplates = Literal[
    "ggplot2",
    "seaborn",
    "simple_white",
    "plotly",
    "plotly_white",
    "plotly_dark",
    "presentation",
    "xgridoff",
    "ygridoff",
    "gridon",
    "none",
]


class PlotlyTickerPlotConfig(PlottingBackendConfig):
    name: Literal[PlottingBackendName.PLOTLY] = PlottingBackendName.PLOTLY
    width: int = 850
    height: int = 500
    scale: float = 4
    num_xticks: int = 10
    metrics_num_cols: int = 3
    scope_id: str = "<SCOPE_ID_PLACEHOLDER>"
    filename_prefix: str = "stock_ticker_history"
    image_format: Literal["jpeg", "png"] = "jpeg"
    template: PlotlyTemplates = "plotly_dark"
    metric_to_display_name: dict[MetricName, str] = {
        MetricName.OPEN: "Open",
        MetricName.HIGH: "High",
        MetricName.CLOSE: "Close",
        MetricName.MARKET_CAP: "Market Cap",
        MetricName.PRICE_EARNINGS_RATIO: "P/E Ratio",
        MetricName.VOLUME: "Volume",
        MetricName.YEAR_HIGH: "Year High",
        MetricName.YEAR_LOW: "Year Low",
        MetricName.DIVIDEND_YIELD: "Dividend Yield",
        MetricName.VOLATILITY_30_DAYS: "Volatility 30 Days",
    }


class PlotlyPlottingBackend(PlottingBackend[PlotlyTickerPlotConfig]):
    def __init__(
        self, config: PlotlyTickerPlotConfig, content_service: ContentService
    ):
        super().__init__(config)
        self.content_service = content_service

    @classmethod
    def get_plotly_plot(
        cls,
        payload: StockHistoryPlotPayload,
        metric_to_display_name: dict[MetricName, str],
        metrics_num_cols: int,
        num_xticks: int,
        template: PlotlyTemplates,
    ) -> go.Figure:
        session_dates = [item.date for item in payload.price_history]
        price_history = [item.value for item in payload.price_history]
        company_name = payload.info.company_name
        ticker = payload.info.ticker
        market_name = payload.info.exchange
        currency = payload.info.currency

        metrics = None
        if payload.metrics is not None:
            metrics = {
                metric_to_display_name.get(
                    metric.name, str(metric.name)
                ): metric.value
                for metric in payload.metrics
            }

        return plot_stock_price_history_plotly(
            session_dates=session_dates,
            price_history=price_history,
            company_name=company_name,
            ticker=ticker,
            market_name=market_name,
            currency=currency,
            metrics=metrics,
            metrics_num_cols=metrics_num_cols,
            num_xticks=num_xticks,
            template=template,
        )

    @override
    def plot(
        self,
        ticker_data: list[StockHistoryPlotPayload],
    ) -> str:
        res_str = ""

        for payload in ticker_data:
            figure = self.get_plotly_plot(
                payload,
                self.config.metric_to_display_name,
                self.config.metrics_num_cols,
                self.config.num_xticks,
                self.config.template,
            )

            content_id = save_plots_to_content_service(
                figs=figure,
                content_service=self.content_service,
                scope_id=self.config.scope_id,
                filename_prefix=self.config.filename_prefix,
                image_format=self.config.image_format,
                height=self.config.height,
                width=self.config.width,
                scale=self.config.scale,
            )

            markdown = get_image_markdown_from_content_id(content_id)
            res_str += f"{markdown}\n"

        return res_str.strip()

    @classmethod
    @override
    def remove_result_from_text(cls, text: str) -> str:
        return text  # At the moment, there is no way to remove the result from the text without removing other images. This is a noop.
