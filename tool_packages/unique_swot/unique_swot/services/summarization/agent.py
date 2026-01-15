from logging import getLogger

from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_swot.services.summarization.config import SummarizationConfig

_LOGGER = getLogger(__name__)


class SummarizationAgent:
    def __init__(
        self,
        *,
        llm: LMI,
        llm_service: LanguageModelService,
        summarization_config: SummarizationConfig,
    ):
        self._llm = llm
        self._llm_service = llm_service
        self.summarization_config = summarization_config

    async def summarize(
        self,
        *,
        company_name: str,
        markdown_report: str,
    ) -> str:
        # Render the report with compatible citations for streaming
        user_prompt = Template(
            self.summarization_config.prompt_config.user_prompt
        ).render(company_name=company_name, report=markdown_report)

        system_prompt = Template(
            self.summarization_config.prompt_config.system_prompt
        ).render()

        messages = (
            MessagesBuilder()
            .system_message_append(system_prompt)
            .user_message_append(user_prompt)
            .build()
        )

        try:
            response = await self._llm_service.complete_async(
                model_name=self._llm.name,
                messages=messages,
            )

            if not isinstance(response.choices[0].message.content, str):
                raise ValueError("Invalid response content received from the LLM")

        except Exception as e:
            # If an error occur during the summarization, we return an empty string
            _LOGGER.exception(f"Error summarizing report: {e}")
            return "An error occurred during summarization. Please try again."

        summarization_result = response.choices[0].message.content

        return summarization_result
