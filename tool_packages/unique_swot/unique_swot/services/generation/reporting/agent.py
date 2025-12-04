from logging import getLogger

from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.extraction.models import SWOTExtractionModel
from unique_swot.services.generation.reporting.config import ReportingConfig
from unique_swot.services.generation.reporting.models import (
    SWOTConsolidatedReport,
    get_swot_consolidated_report_model,
)
from unique_swot.services.generation.reporting.prompts import (
    get_swot_reporting_system_prompt,
)
from unique_swot.services.generation.structured_output import generate_structured_output
from unique_swot.services.memory.base import SwotMemoryService

_LOGGER = getLogger(__name__)


class ProgressiveReportingAgent:
    def __init__(
        self,
        *,
        memory_service: SwotMemoryService,
        llm_service: LanguageModelService,
        llm: LMI,
        reporting_config: ReportingConfig,
    ):
        self._llm_service: LanguageModelService = llm_service
        self._llm = llm
        self._memory_service: SwotMemoryService[SWOTConsolidatedReport] = memory_service
        self._reporting_config: ReportingConfig = reporting_config

    async def generate_and_update_memory(
        self,
        *,
        company_name: str,
        component: SWOTComponent,
        extraction_result: SWOTExtractionModel,
        optional_instruction: str | None,
    ) -> None:
        # Load previous report from memory
        consolidated_report_model = get_swot_consolidated_report_model(component)

        previous_report = self._memory_service.get(consolidated_report_model)

        system_prompt = self._compose_system_prompt(
            company_name=company_name, component=component
        )

        user_prompt = self._compose_user_prompt(
            consolidated_report=previous_report,
            extraction_result=extraction_result,
            optional_instruction=optional_instruction,
        )

        # Generate the new items
        new_items = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_prompt,
            llm_service=self._llm_service,
            llm=self._llm,
            output_model=consolidated_report_model,
        )
        if new_items is not None:
            updated_report = self._update_consolidated_report(
                consolidated_report=previous_report,
                new_items=new_items,
            )
            self._memory_service.set(updated_report)

    def get_report(self) -> str:
        # Get the report from all components

        return ""

    def _compose_system_prompt(
        self, company_name: str, component: SWOTComponent
    ) -> str:
        system_prompt_template = get_swot_reporting_system_prompt(
            component, self._reporting_config.reporting_prompt_config
        )
        return Template(system_prompt_template).render(company_name=company_name)

    def _compose_user_prompt(
        self,
        *,
        consolidated_report: SWOTConsolidatedReport | None,
        extraction_result: SWOTExtractionModel,
        optional_instruction: str | None,
    ) -> str:
        """
        Compose the user prompt for the reporting agent.

        This method renders the user_prompt.j2 template with:
        - previous_report: The current consolidated report state (or None if first run)
        - extraction_items: The new raw extraction items to integrate
        - optional_instruction: User's custom instructions (if any)
        """
        user_prompt_template = (
            self._reporting_config.reporting_prompt_config.user_prompt
        )

        # Prepare the previous report items for rendering
        previous_report_items = None
        if consolidated_report is not None:
            previous_report_items = consolidated_report.get_items()

        # Prepare the extraction items for rendering
        extraction_items = extraction_result.get_items()

        return Template(user_prompt_template).render(
            previous_report_items=previous_report_items,
            extraction_items=extraction_items,
            optional_instruction=optional_instruction,
        )

    def _update_consolidated_report(
        self,
        *,
        consolidated_report: SWOTConsolidatedReport | None,
        new_items: SWOTConsolidatedReport,
    ) -> SWOTConsolidatedReport:
        if consolidated_report is None:
            return new_items

        return consolidated_report.update(new_items)  # type: ignore
