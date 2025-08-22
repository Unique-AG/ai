import logging
from pathlib import Path

import humps
from unique_toolkit.language_model import (
    LanguageModelService,
    Prompt,
    convert_string_to_json,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessages,
)
from unique_toolkit.short_term_memory.service import ShortTermMemoryService

from detection.config import StockTickerDetectionConfig
from detection.memory import StockTickerMemoryManager
from detection.prompt import SYSTEM_MESSAGE_STOCK_TICKER_QUERY, USER_MESSAGE_STOCK_TICKER_QUERY
from detection.schema import StockTickerList, getStockTickersResponse




FOLDER_NAME = Path(__file__).parent.name
EXTERNAL_MODULE_NAME = humps.pascalize(FOLDER_NAME)
logger = logging.getLogger(f"{EXTERNAL_MODULE_NAME}.{__name__}")


class StockTickerService:
    def __init__(
        self,
        language_model_service: LanguageModelService,
        config: StockTickerDetectionConfig,
        memory_manager: StockTickerMemoryManager | None = None,
    ):
        self.language_model_service = language_model_service
        self.config = config
        self._memory_manager = memory_manager

    async def get_stock_tickers(
        self,
        assistant_message: str,
        user_message: str,
    ) -> getStockTickersResponse:
        """
        Get stock tickers from the user and assistant messages
        """
        logger.info("Start StockTickerService")

        messages = await self._prepare_messages(
            assistant_message, user_message
        )

        response = await self.language_model_service.complete_async(
            model_name=self.config.language_model.name,
            messages=messages,
            temperature=0,
            other_options=self.config.additional_llm_options,
        )

        response_content = response.choices[0].message.content

        if not isinstance(response_content, str):
            logger.error("Response content is not a string")
            return getStockTickersResponse(success=False)

        try:
            ticker_list = StockTickerList.model_validate(
                convert_string_to_json(response_content)
            ).tickers
            logger.debug(
                "Found %s tickers: %s",
                len(ticker_list),
                [ticker_elem.ticker for ticker_elem in ticker_list],
            )
            if self._memory_manager is not None:
                ticker_list = self._memory_manager.process_new_tickers(
                    ticker_list
                )
                logger.debug(
                    "Tickers left after memory processing: %s",
                    [ticker_elem.ticker for ticker_elem in ticker_list],
                )
            return getStockTickersResponse(success=True, response=ticker_list)
        except Exception as e:
            logger.error(
                f"Error sanitizing response content: {e}", exc_info=True
            )
            return getStockTickersResponse(success=False)

    async def append_stock_diagram_to_message(
        self, message: str, diagram: str
    ) -> str:
        """Append the diagram to the message"""
        return message + "\n\n" + diagram + "\n\n"

    async def _prepare_messages(
        self, assistant_message: str, user_message: str
    ) -> LanguageModelMessages:
        user_msg = Prompt(
            template=USER_MESSAGE_STOCK_TICKER_QUERY,
            assistant_message=assistant_message,
            user_message=user_message,
        )
        system_msg = Prompt(
            template=SYSTEM_MESSAGE_STOCK_TICKER_QUERY
            + "\n\n"
            + f"Output format: \n {StockTickerList.model_json_schema()}",
        )

        return LanguageModelMessages(
            [
                system_msg.to_system_msg(),
                user_msg.to_user_msg(),
            ]
        )


def get_stock_ticker_service(
    config: StockTickerDetectionConfig,
    company_id: str,
    chat_id: str,
    user_id: str,
    llm_service: LanguageModelService,
) -> StockTickerService:
    memory_manager = None
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        chat_id=chat_id,
        user_id=user_id,
        message_id= None,
    )
    memory_manager = StockTickerMemoryManager.from_short_term_memory_service(
        short_term_memory_service=short_term_memory_service,
        config=config.memory_config,
    )

    return StockTickerService(
        language_model_service=llm_service,
        config=config,
        memory_manager=memory_manager,
    )
