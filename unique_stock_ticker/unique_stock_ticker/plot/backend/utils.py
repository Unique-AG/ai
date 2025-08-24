from unique_toolkit.content.service import ContentService

from unique_stock_ticker.plot.backend.base import (
    PlottingBackend,
    PlottingBackendName,
)
from unique_stock_ticker.plot.backend.next import (
    NextPlottingBackend,
    NextTickerPlotConfig,
)
from unique_stock_ticker.plot.backend.plotly import (
    PlotlyPlottingBackend,
    PlotlyTickerPlotConfig,
)


def get_plotting_backend(
    config: NextTickerPlotConfig | PlotlyTickerPlotConfig,
    chat_id: str,
    user_id: str,
    company_id: str,
) -> PlottingBackend:
    if config.name == PlottingBackendName.PLOTLY:
        content_service = ContentService(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
        )
        return PlotlyPlottingBackend(
            config=config,
            content_service=content_service,
        )
    else:
        return NextPlottingBackend(
            config=config,
        )
