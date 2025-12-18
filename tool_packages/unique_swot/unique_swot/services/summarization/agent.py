from copy import deepcopy
from logging import getLogger

from jinja2 import Template
from unique_toolkit import ChatService
from unique_toolkit._common.validators import LMI
from unique_toolkit.content.utils import _generate_pages_postfix
from unique_toolkit.language_model.builder import MessagesBuilder

from unique_swot.services.citations import CitationManager
from unique_swot.services.generation.models.base import SWOTReportComponents
from unique_swot.services.report import ReportDeliveryService
from unique_swot.services.summarization.config import SummarizationConfig

_LOGGER = getLogger(__name__)


class SummarizationAgent:
    def __init__(
        self,
        *,
        llm: LMI,
        chat_service: ChatService,
        summarization_config: SummarizationConfig,
    ):
        self._llm = llm
        self._chat_service = chat_service
        self.summarization_config = summarization_config

    async def summarize(
        self,
        *,
        company_name: str,
        result: SWOTReportComponents,
        citation_manager: CitationManager,
        report_handler: ReportDeliveryService,
    ) -> tuple[str, str, int]:
        # Render the report with compatible citations for streaming
        markdown_report = report_handler.render_report(
            result=result,
            citation_fn=lambda report: citation_manager.add_citations_to_report(
                report,
                "stream",  # Uses [source1], [source2], [source3]
            ),
        )

        # Get the chunks that were referenced in the report
        chunks = deepcopy(citation_manager.get_referenced_content_chunks())

        # Add pages postfix to the chunks (relevant for frontend display)
        for chunk in chunks:
            pages_postfix = _generate_pages_postfix([chunk])
            chunk.key = chunk.key + pages_postfix if chunk.key else chunk.key
            chunk.title = chunk.title + pages_postfix if chunk.title else chunk.title

        user_prompt = Template(
            self.summarization_config.prompt_config.user_prompt
        ).render(company_name=company_name, report=markdown_report, chunks=chunks)

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
            response = await self._chat_service.complete_with_references_async(
                model_name=self._llm.name,
                messages=messages,
                content_chunks=chunks,
            )

            if response.message.original_text is None:
                raise ValueError("No response content received from the LLM")

        except Exception as e:
            # If an error occur during the summarization, we return an empty string
            _LOGGER.exception(f"Error summarizing report: {e}")
            return "An error occurred during summarization. Please try again.", "", 0

        response_content = response.message.original_text

        # Recover old references
        summarization_result = self._remap_references_to_chunks(
            response_content, citation_manager
        )

        num_references = len(citation_manager.get_citations_map())

        # Reset the citation manager to generate fresh references for the next report
        citation_manager.reset_maps()

        return response.message.text, summarization_result, num_references

    def _remap_references_to_chunks(
        self, response_content: str, citation_manager: CitationManager
    ) -> str:
        citations_map = citation_manager.get_citations_map()
        for chunk_id, source_id in citations_map.items():
            response_content = response_content.replace(
                source_id, f"[chunk_{chunk_id}]"
            )
        return response_content
