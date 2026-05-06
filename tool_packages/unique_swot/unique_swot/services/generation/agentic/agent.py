import json
from collections import defaultdict
from logging import getLogger
from typing import AsyncIterator

from tqdm.asyncio import tqdm
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI
from unique_toolkit.content import Content

from unique_swot.services.generation.agentic.config import AgenticGeneratorConfig
from unique_swot.services.generation.agentic.exceptions import (
    FailedToExtractFactsException,
)
from unique_swot.services.generation.agentic.executor import AgenticPlanExecutor
from unique_swot.services.generation.agentic.operations import (
    extract_facts,
    handle_accumulated_generate_operation,
    handle_generate_operation,
)
from unique_swot.services.generation.agentic.utils import (
    batch_sequence_generator,
    create_batch_notification,
    create_progress_sequence,
)
from unique_swot.services.generation.config import GenerationMode
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTReportComponents,
)
from unique_swot.services.generation.models.registry import SWOTReportRegistry
from unique_swot.services.orchestrator.service import (
    ProgressNotifier,
    SourceRegistry,
    SourceSelector,
    StepNotifier,
)
from unique_swot.services.schemas import SWOTOperation, SWOTPlan
from unique_swot.utils import (
    convert_content_chunk_to_reference,
    generate_unique_id,
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
        config: AgenticGeneratorConfig,
        generation_mode: GenerationMode = GenerationMode.INTERLEAVED,
    ):
        self._llm_service = llm_service
        self._registry = registry
        self._company_name = company_name
        self._swot_report_registry = registry
        self._llm = llm
        self._executor = executor
        self._title = "Generating SWOT report"
        self._config = config
        self._generation_mode = generation_mode

    @property
    def notification_title(self) -> str:
        return self._title

    @notification_title.setter
    def notification_title(self, value: str):
        self._title = value

    async def generate(
        self,
        *,
        plan: SWOTPlan,
        total_steps: int,
        source_iterator: AsyncIterator[Content],
        source_selector: SourceSelector,
        source_registry: SourceRegistry,
        step_notifier: StepNotifier,
        progress_notifier: ProgressNotifier,
    ) -> SWOTReportComponents:
        match self._generation_mode:
            case GenerationMode.INTERLEAVED:
                return await self._generate_interleaved(
                    plan=plan,
                    total_steps=total_steps,
                    source_iterator=source_iterator,
                    source_selector=source_selector,
                    source_registry=source_registry,
                    step_notifier=step_notifier,
                    progress_notifier=progress_notifier,
                )
            case GenerationMode.EXTRACT_FIRST:
                return await self._generate_extract_first(
                    plan=plan,
                    total_steps=total_steps,
                    source_iterator=source_iterator,
                    source_selector=source_selector,
                    source_registry=source_registry,
                    step_notifier=step_notifier,
                    progress_notifier=progress_notifier,
                )
            case _:
                raise ValueError(
                    f"Unsupported generation mode: {self._generation_mode}"
                )

    # ------------------------------------------------------------------
    # Interleaved mode (existing behaviour)
    # ------------------------------------------------------------------

    async def _generate_interleaved(
        self,
        *,
        plan: SWOTPlan,
        total_steps: int,
        source_iterator: AsyncIterator[Content],
        source_selector: SourceSelector,
        source_registry: SourceRegistry,
        step_notifier: StepNotifier,
        progress_notifier: ProgressNotifier,
    ) -> SWOTReportComponents:
        step_size, progress_sequence = create_progress_sequence(
            start=10, stop=80, steps=total_steps
        )
        progress_notifier.step_size = step_size

        async for content in tqdm(
            source_iterator, total=total_steps, desc="Processing sources"
        ):
            await progress_notifier.update(
                progress=next(progress_sequence),
            )

            source_selection_result = await source_selector.select(
                company_name=self._company_name,
                content=content,
                step_notifier=step_notifier,
            )

            if not source_selection_result.should_select:
                _LOGGER.info("Skipping source because it is not selected")
                continue

            _LOGGER.info("Selecting source because it is selected")

            await self._generation_step(
                plan=plan,
                content=content,
                step_notifier=step_notifier,
                source_registry=source_registry,
                progress_notifier=progress_notifier,
            )

        return self._get_swot_report_components()

    # ------------------------------------------------------------------
    # Extract-first mode
    # ------------------------------------------------------------------

    async def _generate_extract_first(
        self,
        *,
        plan: SWOTPlan,
        total_steps: int,
        source_iterator: AsyncIterator[Content],
        source_selector: SourceSelector,
        source_registry: SourceRegistry,
        step_notifier: StepNotifier,
        progress_notifier: ProgressNotifier,
    ) -> SWOTReportComponents:
        step_size, progress_sequence = create_progress_sequence(
            start=10, stop=60, steps=total_steps
        )
        progress_notifier.step_size = step_size

        components_step = plan.convert_plan_to_list_of_steps()
        accumulated_facts: dict[SWOTComponent, list[str]] = defaultdict(list)

        # Phase 1 — extract facts from every source
        async for content in tqdm(
            source_iterator, total=total_steps, desc="Extracting facts"
        ):
            await progress_notifier.update(progress=next(progress_sequence))

            source_selection_result = await source_selector.select(
                company_name=self._company_name,
                content=content,
                step_notifier=step_notifier,
            )

            if not source_selection_result.should_select:
                _LOGGER.info("Skipping source because it is not selected")
                continue

            _LOGGER.info("Selecting source for extraction")

            source_batches = self._prepare_source_batches(
                content=content, source_registry=source_registry
            )

            document_title = get_content_chunk_title(content)
            self.notification_title = f"**Extracting from `{document_title}`**"

            document_reference = convert_content_chunk_to_reference(
                content_or_chunk=content,
            )
            await step_notifier.notify(
                title=self.notification_title,
                sources=[document_reference],
                progress=0,
            )

            batches = list(
                batch_sequence_generator(
                    language_model=self._llm,
                    source_batches=source_batches,
                    max_tokens_per_extraction_batch=self._config.max_tokens_per_extraction_batch,
                    serializer=json.dumps,
                )
            )

            if len(batches) > 1:
                await step_notifier.notify(
                    title=self.notification_title,
                    description=f"This document is too large to extract. It will be split into {len(batches)} batches.",
                )

            for component, step in components_step:
                if step.operation == SWOTOperation.NOT_REQUESTED:
                    continue

                for i, batch in enumerate(batches, start=1):
                    await step_notifier.notify(
                        title=self.notification_title,
                        description=create_batch_notification(
                            component=component.value,
                            batch_index=i,
                            total_batches=len(batches),
                        ),
                    )
                    try:
                        facts = await extract_facts(
                            company_name=self._company_name,
                            component=component,
                            source_batches=batch,
                            step_notifier=step_notifier,
                            llm=self._llm,
                            llm_service=self._llm_service,
                            notification_title=self.notification_title,
                            prompts_config=self._config.prompts_config.extraction_prompt_config,
                            component_definition_prompt_config=self._config.prompts_config.definition_prompt_config,
                        )
                        accumulated_facts[component].extend(facts)
                    except FailedToExtractFactsException:
                        _LOGGER.warning(
                            f"Extraction failed for {component} from {document_title}, batch {i}. Continuing."
                        )

            await step_notifier.notify(
                title=self.notification_title,
                progress=100,
                description=f"Completed extracting from {document_title}!",
                completed=True,
            )

        # Phase 2 — cluster and generate per component
        self.notification_title = "**Generating SWOT report sections**"
        await step_notifier.notify(
            title=self.notification_title,
            description="All facts extracted. Clustering and generating sections...",
            progress=0,
        )

        requested_components = [
            comp
            for comp, step in components_step
            if step.operation != SWOTOperation.NOT_REQUESTED
        ]
        total_components = len(requested_components)

        for idx, component in enumerate(requested_components):
            facts = accumulated_facts.get(component, [])
            if not facts:
                _LOGGER.warning(
                    f"No facts accumulated for component {component}. Skipping."
                )
                continue

            fact_id_map = {generate_unique_id("fact_"): f for f in facts}

            await step_notifier.notify(
                title=self.notification_title,
                description=f"Clustering and generating sections for {component.value}...",
                progress=int(idx / total_components * 100),
            )

            await handle_accumulated_generate_operation(
                component=component,
                fact_id_map=fact_id_map,
                step_notifier=step_notifier,
                company_name=self._company_name,
                llm=self._llm,
                llm_service=self._llm_service,
                notification_title=self.notification_title,
                swot_report_registry=self._swot_report_registry,
                executor=self._executor,
                config=self._config,
            )

            await progress_notifier.increment(
                fraction=1 / total_components if total_components else 1,
            )

        await step_notifier.notify(
            title=self.notification_title,
            progress=100,
            description="Report generation complete!",
            completed=True,
        )

        return self._get_swot_report_components()

    async def _generation_step(
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

        batches_generator = batch_sequence_generator(
            language_model=self._llm,
            source_batches=source_batches,
            max_tokens_per_extraction_batch=self._config.max_tokens_per_extraction_batch,
            serializer=json.dumps,
        )

        batches = list(batches_generator)
        total_batches = len(batches)

        if total_batches > 1:
            await step_notifier.notify(
                title=self.notification_title,
                description=f"This document is too large to extract. It will be split into {len(batches)} batches.",
            )

        for index, (component, step) in enumerate(components_step):
            for i, batch in enumerate(batches, start=1):
                await step_notifier.notify(
                    title=self.notification_title,
                    progress=int(index / len(components_step) * 100),
                    description=create_batch_notification(
                        component=component.value,
                        batch_index=i,
                        total_batches=len(batches),
                    ),
                )
                match step.operation:
                    case SWOTOperation.GENERATE:
                        await handle_generate_operation(
                            component=component,
                            source_batches=batch,
                            step_notifier=step_notifier,
                            company_name=self._company_name,
                            llm=self._llm,
                            llm_service=self._llm_service,
                            notification_title=self.notification_title,
                            swot_report_registry=self._swot_report_registry,
                            executor=self._executor,
                            config=self._config,
                        )
                    case SWOTOperation.MODIFY:
                        _LOGGER.warning(
                            "Modification operation not supported yet. Using generate operation instead."
                        )
                        await handle_generate_operation(
                            component=component,
                            source_batches=batch,
                            step_notifier=step_notifier,
                            company_name=self._company_name,
                            llm=self._llm,
                            llm_service=self._llm_service,
                            notification_title=self.notification_title,
                            swot_report_registry=self._swot_report_registry,
                            executor=self._executor,
                            config=self._config,
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

    def _get_swot_report_components(self) -> SWOTReportComponents:
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
