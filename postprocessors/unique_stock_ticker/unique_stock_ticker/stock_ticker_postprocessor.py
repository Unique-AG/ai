import re

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.language_model.schemas import LanguageModelStreamResponse

from unique_stock_ticker.config import StockTickerConfig
from unique_stock_ticker.integrated import retrieve_tickers_and_plot_history


class StockTickerPostprocessor(Postprocessor):
    """
    Postprocessor for follow-up questions in the loop agent.
    This class handles the processing of follow-up questions based on the
    provided configuration and the results of the evaluation checks.
    """

    def __init__(
        self,
        config: StockTickerConfig,
        event: ChatEvent,
    ):
        super().__init__(name="StockTickerPostprocessor")
        self._config = config
        self._company_id = event.company_id
        self._user_id = event.user_id
        self._chat_id = event.payload.chat_id
        self._user_message = event.payload.user_message.text

    async def run(self, loop_response: LanguageModelStreamResponse) -> None:
        self._text = await retrieve_tickers_and_plot_history(
            company_id=self._company_id,
            user_id=self._user_id,
            chat_id=self._chat_id,
            stock_ticker_config=self._config,
            assistant_message=loop_response.message.text,
            user_message=self._user_message,
        )

    def apply_postprocessing_to_response(
        self, loop_response: LanguageModelStreamResponse
    ) -> bool:
        if not self._text or len(self._text) == 0:
            return False
        # Append the follow-up question suggestions to the loop response
        loop_response.message.text += "\n" + self._text
        return True

    async def remove_from_text(self, text: str) -> str:
        return re.sub(r"```financialChart[\s\S]*?```", "", text)
