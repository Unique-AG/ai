import json
from logging import getLogger

from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import Content

from unique_swot.services.generation.agentic.exceptions import (
    FailedToCreateNewSectionException,
    FailedToExtractFactsException,
    FailedToGeneratePlanException,
    FailedToUpdateExistingSectionException,
    InvalidCommandException,
    InvalidPlanException,
    SectionNotFoundException,
)
from unique_swot.services.generation.agentic.executor import AgenticPlanExecutor
from unique_swot.services.generation.agentic.prompts.commands import (
    CREATE_NEW_SECTION_SYSTEM_PROMPT,
    CREATE_NEW_SECTION_USER_PROMPT,
    UPDATE_EXISTING_SECTION_SYSTEM_PROMPT,
    UPDATE_EXISTING_SECTION_USER_PROMPT,
)
from unique_swot.services.generation.agentic.prompts.definition import (
    get_component_definition,
)
from unique_swot.services.generation.agentic.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
)
from unique_swot.services.generation.agentic.prompts.plan import (
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_PROMPT,
)
from unique_swot.services.generation.agentic.utils import create_map_from_list
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTExtractionFactsList,
    SWOTReportComponents,
    SWOTReportComponentSection,
)
from unique_swot.services.generation.models.plan import (
    GenerationPlan,
    GenerationPlanCommand,
    GenerationPlanCommandType,
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
    generate_structured_output,
    get_content_chunk_title,
)

_LOGGER = getLogger(__name__)


class GenerationAngent:
    def __init__(
        self,
        *,
        company_name: str,
        llm: LMI,
        llm_service: LanguageModelService,
        registry: SWOTReportRegistry,
        executor: AgenticPlanExecutor,
    ):
        self._llm_service = llm_service
        self._registry = registry
        self._company_name = company_name
        self._swot_report_registry = registry
        self._llm = llm
        self._executor = executor
        self._title = "Generating SWOT report"

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
        _LOGGER.info(
            f"Executing SWOT analysis for {self._company_name} with plan {plan.model_dump_json(indent=1)}"
        )
        # Prepare the source splits
        components_step = plan.convert_plan_to_list_of_steps()
        source_batches = self._prepare_source_batches(
            content=content, source_registry=source_registry
        )

        document_title = get_content_chunk_title(content)
        self.notification_title = f"**Processing {document_title}**"

        document_reference = convert_content_chunk_to_reference(
            content_or_chunk=content,
        )

        await step_notifier.notify(
            title=self.notification_title,
            sources=[document_reference],
        )

        increment_step = 1 / len(components_step)

        for component, step in components_step:
            match step.operation:
                case SWOTOperation.GENERATE:
                    await self._handle_generate(
                        component=component,
                        source_batches=source_batches,
                        step_notifier=step_notifier,
                    )
                case SWOTOperation.MODIFY:
                    await self._handle_modify(
                        component=component,
                        source_batches=source_batches,
                        instruction=step.modify_instruction,
                        step_notifier=step_notifier,
                    )
                case SWOTOperation.NOT_REQUESTED:
                    continue
                case _:
                    raise ValueError(f"Invalid operation: {step.operation}")

            await progress_notifier.increment_progress(
                step_increment=increment_step,
                progress_info=f"Processing {component} for {document_title}...",
            )

    async def _handle_generate(
        self,
        *,
        component: SWOTComponent,
        source_batches: list[dict[str, str]],
        step_notifier: StepNotifier,
    ) -> None:
        # Extract the items for the component
        extracted_facts = await self._extract(
            component=component,
            source_batches=source_batches,
            step_notifier=step_notifier,
        )

        # Skip if list of facts is empty
        if len(extracted_facts) == 0:
            _LOGGER.warning(
                f"No facts extracted for component {component}. Skipping..."
            )
            return

        fact_id_map = create_map_from_list(prefix="fact", items=extracted_facts)

        # Plan the generation for the component
        plan = await self._plan(
            component=component, fact_id_map=fact_id_map, step_notifier=step_notifier
        )

        # Execute the generation for the component
        await self._execute(plan=plan, component=component, fact_id_map=fact_id_map)

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

    async def _extract(
        self,
        *,
        component: SWOTComponent,
        source_batches: list[dict[str, str]],
        step_notifier: StepNotifier,
    ) -> list[str]:
        system_prompt = EXTRACTION_SYSTEM_PROMPT.render(
            company_name=self._company_name,
            component=component,
            component_definition=get_component_definition(component),
        )
        user_message = EXTRACTION_USER_PROMPT.render(
            company_name=self._company_name,
            component=component,
            source_batches=source_batches,
        )

        extracted_facts = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_message,
            llm_service=self._llm_service,
            llm=self._llm,
            output_model=SWOTExtractionFactsList,
        )

        if extracted_facts is None:
            _LOGGER.error(f"Failed to extract facts for component {component}")
            raise FailedToExtractFactsException(
                f"Failed to extract facts for component {component}"
            )
        _LOGGER.debug(
            f"Extracted facts for component {component}:\n {extracted_facts.model_dump_json(indent=1)}"
        )
        await step_notifier.notify(
            title=self.notification_title,
            description=extracted_facts.notification_message,
        )
        return extracted_facts.facts

    async def _plan(
        self,
        *,
        component: SWOTComponent,
        fact_id_map: dict[str, str],
        step_notifier: StepNotifier,
    ) -> GenerationPlan:
        system_prompt = PLAN_SYSTEM_PROMPT.render(
            company_name=self._company_name,
            component=component,
        )

        existing_sections_view = (
            self._swot_report_registry.retrieve_sections_for_component(
                component=component,
                exclude_items=False,
            )
        )

        fact_view = json.dumps(fact_id_map, indent=1)

        user_message = PLAN_USER_PROMPT.render(
            fact_view=fact_view,
            existing_sections_view=existing_sections_view,
        )

        plan = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_message,
            llm_service=self._llm_service,
            llm=self._llm,
            output_model=GenerationPlan,
        )
        if plan is None:
            _LOGGER.error(f"Failed to generate plan for component {component}")
            raise FailedToGeneratePlanException(
                f"Failed to generate plan for component {component}"
            )

        _LOGGER.debug(
            f"Generated plan for component {component}:\n {plan.model_dump_json(indent=1)}"
        )
        await step_notifier.notify(
            title=self.notification_title,
            description=plan.notification_message,
        )
        return plan

    async def _execute(
        self,
        *,
        plan: GenerationPlan,
        component: SWOTComponent,
        fact_id_map: dict[str, str],
    ):
        for command in plan.commands:
            match command.command:
                case GenerationPlanCommandType.CREATE_SECTION:
                    self._executor.add(
                        self._handle_create_new_section,
                        component=component,
                        instruction=command.instruction,
                        command=command,
                        fact_id_map=fact_id_map,
                    )

                case GenerationPlanCommandType.UPDATE_SECTION:
                    self._executor.add(
                        self._handle_update_existing_section,
                        component=component,
                        instruction=command.instruction,
                        command=command,
                        fact_id_map=fact_id_map,
                    )
                case _:
                    raise InvalidCommandException(f"Invalid command: {command.command}")

        results = await self._executor.run()

        for command, result in zip(plan.commands, results):
            if isinstance(result, Exception):
                _LOGGER.debug(
                    f"Exception: {result}\nCommand: {command.model_dump_json(indent=1)}"
                )
            else:
                match command.command:
                    case GenerationPlanCommandType.CREATE_SECTION:
                        self._swot_report_registry.register_section(
                            component=component, section=result
                        )
                    case GenerationPlanCommandType.UPDATE_SECTION:
                        self._swot_report_registry.update_section(
                            id=command.target_section_id,  # type: ignore (if target id is None, the result is not a section)
                            section=result,
                        )
                    case _:
                        raise InvalidCommandException(
                            f"Invalid command: {command.command}"
                        )

    async def _handle_create_new_section(
        self,
        *,
        component: SWOTComponent,
        instruction: str,
        command: GenerationPlanCommand,
        fact_id_map: dict[str, str],
    ) -> SWOTReportComponentSection:
        ## Prepare a fact view for the prompt
        facts = {
            key: value
            for key, value in fact_id_map.items()
            if key in command.source_facts_ids
        }

        ## Prepare the prompt
        system_prompt = CREATE_NEW_SECTION_SYSTEM_PROMPT.render(
            component=component,
            company_name=self._company_name,
        )
        user_message = CREATE_NEW_SECTION_USER_PROMPT.render(
            facts=facts,
            instruction=instruction,
            model_name=SWOTReportComponentSection.__name__,
            model_schema=json.dumps(
                SWOTReportComponentSection.model_json_schema(), indent=1
            ),
        )

        ## Generate the section
        created_section = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_message,
            llm_service=self._llm_service,
            llm=self._llm,
            output_model=SWOTReportComponentSection,
        )

        ## Validate the result
        if created_section is None:
            raise FailedToCreateNewSectionException(
                f"Failed to create new section for component {component}"
            )

        _LOGGER.debug(
            f"Created section for component {component}:\n {created_section.model_dump_json(indent=1)}"
        )

        return created_section

    async def _handle_update_existing_section(
        self,
        *,
        component: SWOTComponent,
        instruction: str,
        command: GenerationPlanCommand,
        fact_id_map: dict[str, str],
    ) -> SWOTReportComponentSection:
        ## Validate the command
        if command.target_section_id is None:
            raise InvalidPlanException(
                f"Target section ID is required for {command.command} command"
            )

        ## Retrieve the existing section
        existing_section = self._swot_report_registry.retrieve_section(
            id=command.target_section_id
        )

        ## Validate section exists
        if existing_section is None:
            raise SectionNotFoundException(
                f"Section with id {command.target_section_id} not found"
            )

        ## Prepare a fact view for the prompt
        facts = {
            key: value
            for key, value in fact_id_map.items()
            if key in command.source_facts_ids
        }

        ## Prepare the system prompt
        system_prompt = UPDATE_EXISTING_SECTION_SYSTEM_PROMPT.render(
            component=component,
            company_name=self._company_name,
        )

        ## Prepare the user message
        user_message = UPDATE_EXISTING_SECTION_USER_PROMPT.render(
            instruction=instruction,
            facts=facts,
            section=existing_section.model_dump_json(indent=1),
            model_name=SWOTReportComponentSection.__name__,
            model_schema=json.dumps(
                SWOTReportComponentSection.model_json_schema(), indent=1
            ),
        )
        ## Generate the section
        updated_section = await generate_structured_output(
            system_prompt=system_prompt,
            user_message=user_message,
            llm_service=self._llm_service,
            llm=self._llm,
            output_model=SWOTReportComponentSection,
        )
        ## Validate the result
        if updated_section is None:
            raise FailedToUpdateExistingSectionException(
                f"Failed to update existing section for component {component}"
            )

        _LOGGER.debug(
            f"Updated section for component {component}:\n {updated_section.model_dump_json(indent=1)}"
        )
        return updated_section

    async def _handle_modify(
        self,
        *,
        component: SWOTComponent,
        instruction: str | None,
        source_batches: list[dict[str, str]],
        step_notifier: StepNotifier,
    ) -> None:
        await self._handle_generate(
            component=component,
            source_batches=source_batches,
            step_notifier=step_notifier,
        )

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
