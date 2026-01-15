from logging import getLogger

from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import Content

from unique_swot.services.generation.agentic.executor import AgenticPlanExecutor
from unique_swot.services.generation.agentic.operations import (
    handle_generate_operation,
)
from unique_swot.services.generation.agentic.prompts.config import AgenticPromptsConfig
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
)
from unique_swot.services.generation.models.registry import SWOTReportRegistry
from unique_swot.services.orchestrator.service import (
    ProgressNotifier,
    SourceRegistry,
    StepNotifier,
)
from unique_swot.services.schemas import SWOTOperation, SWOTPlan
from unique_swot.utils import (
    convert_content_chunk_to_reference,
    get_content_chunk_title,
)

_LOGGER = getLogger(__name__)


class GenerationAgent:
    def __init__(
        self,
        *,
        company_name: str,
        llm: LMI,
        llm_service: LanguageModelService,
        registry: SWOTReportRegistry,
        executor: AgenticPlanExecutor,
        prompts_config: AgenticPromptsConfig,
    ):
        self._llm_service = llm_service
        self._registry = registry
        self._company_name = company_name
        self._swot_report_registry = registry
        self._llm = llm
        self._executor = executor
        self._title = "Generating SWOT report"
        self._prompts_config = prompts_config

    @property
    def notification_title(self) -> str:
        return self._title

    @notification_title.setter
    def notification_title(self, value: str):
        self._title = value

    async def generate(
        self,
        *,
        content: Content,
        source_registry: SourceRegistry,
        plan: SWOTPlan,
        step_notifier: StepNotifier,
        progress_notifier: ProgressNotifier,
    ):
        _LOGGER.info("Starting SWOT Analysis generation Agent")
        # Prepare the source splits
        components_step = plan.convert_plan_to_list_of_steps()
        source_batches = self._prepare_source_batches(
            content=content, source_registry=source_registry
        )

        document_title = get_content_chunk_title(content)
        self.notification_title = f"**Processing `{document_title}`**"

        document_reference = convert_content_chunk_to_reference(
            content_or_chunk=content,
        )

        await step_notifier.notify(
            title=self.notification_title,
            sources=[document_reference],
            progress=0,
        )

        fraction_step = 1 / len(components_step)

        for index, (component, step) in enumerate(components_step):
            await step_notifier.notify(
                title=self.notification_title,
                progress=int(index / len(components_step) * 100),
                description=f"Processing {component.value}...",
            )
            match step.operation:
                case SWOTOperation.GENERATE:
                    await handle_generate_operation(
                        component=component,
                        source_batches=source_batches,
                        step_notifier=step_notifier,
                        company_name=self._company_name,
                        llm=self._llm,
                        llm_service=self._llm_service,
                        notification_title=self.notification_title,
                        swot_report_registry=self._swot_report_registry,
                        executor=self._executor,
                        prompts_config=self._prompts_config,
                    )
                case SWOTOperation.MODIFY:
                    _LOGGER.warning(
                        "Modification operation not supported yet. Using generate operation instead."
                    )
                    await handle_generate_operation(
                        component=component,
                        source_batches=source_batches,
                        step_notifier=step_notifier,
                        company_name=self._company_name,
                        llm=self._llm,
                        llm_service=self._llm_service,
                        notification_title=self.notification_title,
                        swot_report_registry=self._swot_report_registry,
                        executor=self._executor,
                        prompts_config=self._prompts_config,
                    )
                case SWOTOperation.NOT_REQUESTED:
                    continue
                case _:
                    raise ValueError(f"Invalid operation: {step.operation}")

            await progress_notifier.increment(fraction=fraction_step)

        await step_notifier.notify(
            title=self.notification_title,
            progress=100,
            description=f"Completed processing {document_title}!",
            completed=True,
        )

    def _prepare_source_batches(
        self, *, content: Content, source_registry: SourceRegistry
    ) -> list[dict[str, str]]:
        """
        Prepare source chunks for prompting while keeping chunk ids for citation.

        Each entry contains the chunk id and text so downstream prompts can
        instruct the model to cite using [chunk_id].
        """
        ## Register the chunks
        chunk_ids: list[str] = []
        ordered_chunks = sorted(content.chunks, key=lambda x: x.order)
        for chunk in ordered_chunks:
            chunk_id = source_registry.register(chunk=chunk)
            chunk_ids.append(chunk_id)

        return [
            {"id": chunk_id, "text": chunk.text}
            for chunk_id, chunk in zip(chunk_ids, ordered_chunks)
        ]

    def get_reports(self) -> SWOTReportComponents:
        return SWOTReportComponents(
            strengths=self._swot_report_registry.retrieve_component_sections(
                component=SWOTComponent.STRENGTHS
            ),
            weaknesses=self._swot_report_registry.retrieve_component_sections(
                component=SWOTComponent.WEAKNESSES
            ),
            opportunities=self._swot_report_registry.retrieve_component_sections(
                component=SWOTComponent.OPPORTUNITIES
            ),
            threats=self._swot_report_registry.retrieve_component_sections(
                component=SWOTComponent.THREATS
            ),
        )
