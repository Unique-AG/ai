from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.source_management.schema import Source
from unique_swot.services.source_management.selection.config import (
    SourceSelectionConfig,
)
from unique_swot.services.source_management.selection.schema import (
    SourceSelectionResult,
)
from unique_swot.utils import generate_structured_output


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
        self, *, company_name: str, source: Source
    ) -> SourceSelectionResult:
        system_prompt = self._compose_system_prompt(company_name=company_name)
        user_prompt = self._compose_user_prompt(
            company_name=company_name, source=source
        )

        response = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_prompt,
            llm=self._llm,
            llm_service=self._llm_service,
            output_model=SourceSelectionResult,
        )
        if response is None:
            return SourceSelectionResult(
                should_select=False,
                reason="Failed to select the source",
                notification_message="Failed to select the source",
                progress_notification_message="Failed to select the source",
            )

        return response

    def _compose_system_prompt(self, *, company_name: str) -> str:
        template = Template(self._source_selection_config.prompt_config.system_prompt)
        return template.render(company_name=company_name)

    def _compose_user_prompt(self, *, company_name: str, source: Source) -> str:
        selected_chunks = source.chunks[
            : self._source_selection_config.max_number_of_selected_chunks
        ]

        template = Template(self._source_selection_config.prompt_config.user_prompt)
        return template.render(
            company_name=company_name, selected_chunks=selected_chunks
        )
