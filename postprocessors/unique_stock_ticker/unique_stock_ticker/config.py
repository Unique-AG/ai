from datetime import date, timedelta
from logging import getLogger
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from typing_extensions import deprecated
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

from unique_stock_ticker.detection.config import StockTickerDetectionConfig
from unique_stock_ticker.detection.memory import StockTickerMemoryConfig
from unique_stock_ticker.plot.backend.next import NextTickerPlotConfig
from unique_stock_ticker.plot.backend.plotly.plotly import PlotlyTickerPlotConfig
from unique_stock_ticker.plot.config import StockTickerDataRetrievalConfig

logger = getLogger(__name__)


@deprecated(
    "Use StockTickerConfig instead. This format of the config is only kept for backwards compatibility with existing configs."
)
class StockTickerConfigOld(BaseModel):
    model_config = ConfigDict(
        get_configuration_dict(),
        extra="forbid",
    )
    language_model: LMI = LanguageModelInfo.from_name(
        LanguageModelName.AZURE_GPT_4o_2024_1120,
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    memory_config: StockTickerMemoryConfig = StockTickerMemoryConfig()
    enable_stock_tickers: bool = Field(
        default=False,
        description="Whether to enable stock ticker detection.",
    )
    start_date: date = Field(
        default_factory=lambda: date(date.today().year, 1, 1)  # Start of year
    )
    period: timedelta = timedelta(minutes=30)
    plots_config: NextTickerPlotConfig | PlotlyTickerPlotConfig = Field(
        default=PlotlyTickerPlotConfig(), discriminator="name"
    )


class StockTickerConfig(BaseModel):
    model_config = get_configuration_dict()

    data_retrieval_config: StockTickerDataRetrievalConfig = (
        StockTickerDataRetrievalConfig()
    )
    detection_config: StockTickerDetectionConfig = StockTickerDetectionConfig()
    plotting_config: NextTickerPlotConfig | PlotlyTickerPlotConfig = Field(
        default=PlotlyTickerPlotConfig(), discriminator="name"
    )
    enabled: bool = Field(
        default=False,
        description="Whether to enable stock ticker detection.",
    )

    @model_validator(mode="before")
    @classmethod
    def check_if_old_config_is_used(cls, data: Any) -> Any:
        try:
            old_config = StockTickerConfigOld.model_validate(data)

            logger.warning(
                "Old stock ticker config is used. Please update your config to the new format."
            )

            return dict(
                enabled=old_config.enable_stock_tickers,
                data_retrieval_config=StockTickerDataRetrievalConfig(
                    start_date=old_config.start_date,
                    period=old_config.period,
                ),
                plotting_config=old_config.plots_config,
                detection_config=StockTickerDetectionConfig(
                    language_model=old_config.language_model,
                    additional_llm_options=old_config.additional_llm_options,
                    memory_config=old_config.memory_config,
                ),
            )

        except ValueError:
            return data  # Use new config validation
