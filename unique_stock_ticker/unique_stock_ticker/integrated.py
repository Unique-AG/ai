from unique_stock_ticker.clients.six.client import get_six_api_client
from unique_stock_ticker.clients.six.schema.common.instrument import InstrumentType
from unique_stock_ticker.config import StockTickerConfig
from unique_stock_ticker.detection.service import get_stock_ticker_service
from unique_stock_ticker.plot.backend.utils import get_plotting_backend
from unique_stock_ticker.plot.retrieve_and_plot import find_and_plot_history_for_tickers
from unique_toolkit.language_model.service import LanguageModelService


async def retrieve_tickers_and_plot_history(
    company_id: str,
    chat_id: str,
    user_id: str,
    stock_ticker_config: StockTickerConfig,
    assistant_message: str,
    user_message: str,
) -> str:
    if not stock_ticker_config.enabled:
        return ""

    # Get stock ticker service
    llm_service = LanguageModelService(
        company_id=company_id,
        user_id=user_id,
    )
    
    stock_ticker_service = get_stock_ticker_service(
        config=stock_ticker_config.detection_config,
        company_id=company_id,
        chat_id=chat_id,
        user_id=user_id,
        llm_service=llm_service,
    )

    # Get six client
    client = get_six_api_client(company_id=company_id)

    # Plotting backend
    plotting_backend = get_plotting_backend(
        config=stock_ticker_config.plotting_config,
        chat_id=chat_id,
        user_id=user_id,
        company_id=company_id,
    )

    stock_ticker_service_result = await stock_ticker_service.get_stock_tickers(
        assistant_message=assistant_message,
        user_message=user_message,
    )
    if (
        not stock_ticker_service_result.success
        or stock_ticker_service_result.response is None
    ):
        return ""
    found_tickers = [r.ticker for r in stock_ticker_service_result.response]

    instrument_types = [
        InstrumentType.EQUITY
        if r.instrument_type == "equity"
        else InstrumentType.TRUST_SHARE
        for r in stock_ticker_service_result.response
    ]
    return await find_and_plot_history_for_tickers(
        client=client,
        plotting_backend=plotting_backend,
        tickers=found_tickers,
        instrument_types=instrument_types,
        start_date=stock_ticker_config.data_retrieval_config.start_date,
        period=stock_ticker_config.data_retrieval_config.period,
    )
