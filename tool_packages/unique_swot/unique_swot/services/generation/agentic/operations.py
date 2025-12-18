import json
from logging import getLogger
from typing import Any, Sequence

from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.generation.agentic.commands import (
    create_new_section,
    update_existing_section,
)
from unique_swot.services.generation.agentic.exceptions import (
    FailedToExtractFactsException,
    FailedToGeneratePlanException,
    InvalidCommandException,
)
from unique_swot.services.generation.agentic.executor import AgenticPlanExecutor
from unique_swot.services.generation.agentic.prompts.commands.config import (
    CommandsPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.config import AgenticPromptsConfig
from unique_swot.services.generation.agentic.prompts.definition import (
    get_component_definition,
)
from unique_swot.services.generation.agentic.prompts.extraction.config import (
    ExtractionPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.plan.config import PlanPromptConfig
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import SWOTExtractionFactsList
from unique_swot.services.generation.models.plan import (
    GenerationPlan,
    GenerationPlanCommandType,
)
from unique_swot.services.generation.models.registry import SWOTReportRegistry
from unique_swot.services.orchestrator.service import StepNotifier
from unique_swot.utils import generate_structured_output, generate_unique_id

_LOGGER = getLogger(__name__)


async def handle_generate_operation(
    *,
    component: SWOTComponent,
    source_batches: list[dict[str, str]],
    step_notifier: StepNotifier,
    company_name: str,
    llm: LMI,
    llm_service: LanguageModelService,
    notification_title: str,
    swot_report_registry: SWOTReportRegistry,
    executor: AgenticPlanExecutor,
    prompts_config: AgenticPromptsConfig,
) -> None:
    # Extract the items for the component
    extracted_facts = await _extract_facts(
        company_name=company_name,
        component=component,
        source_batches=source_batches,
        step_notifier=step_notifier,
        llm=llm,
        llm_service=llm_service,
        notification_title=notification_title,
        prompts_config=prompts_config.extraction_prompt_config,
    )

    # Skip if list of facts is empty
    if len(extracted_facts) == 0:
        _LOGGER.warning(f"No facts extracted for component {component}. Skipping...")
        return

    fact_id_map = {generate_unique_id("fact_"): fact for fact in extracted_facts}

    # Plan the generation for the component
    plan = await _generate_plan(
        component=component,
        fact_id_map=fact_id_map,
        step_notifier=step_notifier,
        company_name=company_name,
        llm=llm,
        llm_service=llm_service,
        notification_title=notification_title,
        swot_report_registry=swot_report_registry,
        prompts_config=prompts_config.plan_prompt_config,
    )

    # Execute the generation for the component
    results = await _execute_plan(
        plan=plan,
        component=component,
        fact_id_map=fact_id_map,
        swot_report_registry=swot_report_registry,
        llm=llm,
        llm_service=llm_service,
        company_name=company_name,
        executor=executor,
        prompts_config=prompts_config.commands_prompt_config,
    )

    # Register or update the sections in the registry
    _handle_execution_results(
        plan=plan,
        results=results,
        component=component,
        swot_report_registry=swot_report_registry,
    )


async def _extract_facts(
    *,
    company_name: str,
    component: SWOTComponent,
    source_batches: list[dict[str, str]],
    step_notifier: StepNotifier,
    llm: LMI,
    llm_service: LanguageModelService,
    notification_title: str,
    prompts_config: ExtractionPromptConfig,
) -> list[str]:
    system_prompt = Template(prompts_config.system_prompt).render(
        company_name=company_name,
        component=component,
        component_definition=get_component_definition(component),
    )
    user_message = Template(prompts_config.user_prompt).render(
        company_name=company_name,
        component=component,
        source_batches=source_batches,
    )

    extracted_facts = await generate_structured_output(
        system_prompt=system_prompt,
        user_message=user_message,
        llm_service=llm_service,
        llm=llm,
        output_model=SWOTExtractionFactsList,
    )

    if extracted_facts is None:
        _LOGGER.error(f"Failed to extract facts for component {component}")
        raise FailedToExtractFactsException(
            f"Failed to extract facts for component {component}"
        )
    _LOGGER.info(f"Extracted facts for component {component}")
    await step_notifier.notify(
        title=notification_title,
        description=extracted_facts.notification_message,
    )
    return extracted_facts.facts


async def _generate_plan(
    *,
    component: SWOTComponent,
    fact_id_map: dict[str, str],
    step_notifier: StepNotifier,
    company_name: str,
    llm: LMI,
    llm_service: LanguageModelService,
    notification_title: str,
    swot_report_registry: SWOTReportRegistry,
    prompts_config: PlanPromptConfig,
) -> GenerationPlan:
    system_prompt = Template(prompts_config.system_prompt).render(
        company_name=company_name,
        component=component,
    )

    existing_sections_view = swot_report_registry.retrieve_sections_for_component(
        component=component,
        exclude_items=False,
    )

    fact_view = json.dumps(fact_id_map, indent=1)

    user_message = Template(prompts_config.user_prompt).render(
        fact_view=fact_view,
        existing_sections_view=existing_sections_view,
    )

    plan = await generate_structured_output(
        system_prompt=system_prompt,
        user_message=user_message,
        llm_service=llm_service,
        llm=llm,
        output_model=GenerationPlan,
    )
    if plan is None:
        _LOGGER.error(f"Failed to generate plan for component {component}")
        raise FailedToGeneratePlanException(
            f"Failed to generate plan for component {component}"
        )

    _LOGGER.info(f"Generated plan for component {component}")
    await step_notifier.notify(
        title=notification_title,
        description=plan.notification_message,
    )
    return plan


async def _execute_plan(
    *,
    plan: GenerationPlan,
    component: SWOTComponent,
    fact_id_map: dict[str, str],
    swot_report_registry: SWOTReportRegistry,
    llm: LMI,
    llm_service: LanguageModelService,
    company_name: str,
    executor: AgenticPlanExecutor,
    prompts_config: CommandsPromptConfig,
) -> Sequence[Exception | Any]:
    for command in plan.commands:
        match command.command:
            case GenerationPlanCommandType.CREATE_SECTION:
                executor.add(
                    create_new_section,
                    llm=llm,
                    llm_service=llm_service,
                    company_name=company_name,
                    component=component,
                    instruction=command.instruction,
                    command=command,
                    fact_id_map=fact_id_map,
                    prompts_config=prompts_config.create_new_section_prompt_config,
                )

            case GenerationPlanCommandType.UPDATE_SECTION:
                executor.add(
                    update_existing_section,
                    llm=llm,
                    llm_service=llm_service,
                    company_name=company_name,
                    component=component,
                    instruction=command.instruction,
                    command=command,
                    fact_id_map=fact_id_map,
                    swot_report_registry=swot_report_registry,
                    prompts_config=prompts_config.update_existing_section_prompt_config,
                )
            case _:
                raise InvalidCommandException(f"Invalid command: {command.command}")

    results = await executor.run()

    return results


def _handle_execution_results(
    *,
    plan: GenerationPlan,
    results: Sequence[Exception | Any],
    component: SWOTComponent,
    swot_report_registry: SWOTReportRegistry,
) -> None:
    for command, result in zip(plan.commands, results):
        if isinstance(result, Exception):
            _LOGGER.exception(
                f"Error executing command {command.command}", exc_info=result
            )
        else:
            match command.command:
                case GenerationPlanCommandType.CREATE_SECTION:
                    swot_report_registry.register_section(
                        component=component, section=result
                    )
                case GenerationPlanCommandType.UPDATE_SECTION:
                    swot_report_registry.update_section(
                        id=command.target_section_id,  # type: ignore (if target id is None, the result is not a section)
                        section=result,
                    )
                case _:
                    raise InvalidCommandException(f"Invalid command: {command.command}")
