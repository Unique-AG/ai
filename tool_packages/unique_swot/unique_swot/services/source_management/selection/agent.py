from logging import getLogger

from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import Content

from unique_swot.services.orchestrator.service import StepNotifier
from unique_swot.services.source_management.selection.config import (
    SourceSelectionConfig,
)
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)
from unique_swot.utils import generate_structured_output, get_content_chunk_title

_LOGGER = getLogger(__name__)


class SourceSelectionAgent:
    def __init__(
        self,
        *,
        llm_service: LanguageModelService,
        llm: LMI,
        source_selection_config: SourceSelectionConfig,
    ):
        self._llm_service = llm_service
        self._llm = llm
        self._source_selection_config = source_selection_config

    async def select(
        self, *, company_name: str, content: Content, step_notifier: StepNotifier
    ) -> SourceSelectionResult:
        _LOGGER.info(f"Selecting sources for {company_name}")
        system_prompt = self._compose_system_prompt(company_name=company_name)
        user_prompt = self._compose_user_prompt(
            company_name=company_name, content=content
        )
        document_title = get_content_chunk_title(content)
        notification_title = f"Reviewing `{document_title}`"

        await step_notifier.notify(
            title=notification_title,
        )

        response = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_prompt,
            llm=self._llm,
            llm_service=self._llm_service,
            output_model=SourceSelectionResult,
        )

        if response is None:
            _LOGGER.error(f"Failed to select the source for {company_name}")
            response = SourceSelectionResult(
                should_select=True,
                reason="An error occured while selecting the source.",
                notification_message="An error occured while selecting the source. The source will be still considered for the SWOT as a safety measure.",
            )
        await step_notifier.notify(
            title=notification_title,
            description=response.notification_message,
            completed=True,
            progress=100,
        )
        return response

    def _compose_system_prompt(self, *, company_name: str) -> str:
        template = Template(self._source_selection_config.prompt_config.system_prompt)
        return template.render(company_name=company_name)

    def _compose_user_prompt(self, *, company_name: str, content: Content) -> str:
        selected_chunks = content.chunks[
            : self._source_selection_config.max_number_of_selected_chunks
        ]
        selected_chunks_texts = [chunk.text for chunk in selected_chunks]

        template = Template(self._source_selection_config.prompt_config.user_prompt)
        return template.render(
            company_name=company_name, selected_chunks=selected_chunks_texts
        )
