import json
from logging import getLogger

from jinja2 import Template
from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.generation.agentic.exceptions import (
    FailedToCreateNewSectionException,
    FailedToUpdateExistingSectionException,
    InvalidPlanException,
    SectionNotFoundException,
)
from unique_swot.services.generation.agentic.prompts.commands.create_new_section.config import (
    CreateNewSectionPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.commands.update_existing_section.config import (
    UpdateExistingSectionPromptConfig,
)
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.services.generation.models.base import (
    SWOTReportComponentSection,
)
from unique_swot.services.generation.models.plan import GenerationPlanCommand
from unique_swot.services.generation.models.registry import SWOTReportRegistry
from unique_swot.utils import generate_structured_output

_LOGGER = getLogger(__name__)


async def create_new_section(
    *,
    llm: LMI,
    llm_service: LanguageModelService,
    company_name: str,
    component: SWOTComponent,
    instruction: str,
    command: GenerationPlanCommand,
    fact_id_map: dict[str, str],
    prompts_config: CreateNewSectionPromptConfig,
) -> SWOTReportComponentSection:
    ## Prepare a fact view for the prompt
    facts = {
        key: value
        for key, value in fact_id_map.items()
        if key in command.source_facts_ids
    }

    ## Prepare the prompt
    system_prompt = Template(prompts_config.system_prompt).render(
        component=component,
        company_name=company_name,
    )
    user_message = Template(prompts_config.user_prompt).render(
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
        llm_service=llm_service,
        llm=llm,
        output_model=SWOTReportComponentSection,
    )

    ## Validate the result
    if created_section is None:
        raise FailedToCreateNewSectionException(
            f"Failed to create new section for component {component}"
        )

    _LOGGER.info(f"Created section for component {component}")

    return created_section


async def update_existing_section(
    *,
    llm: LMI,
    llm_service: LanguageModelService,
    company_name: str,
    component: SWOTComponent,
    instruction: str,
    command: GenerationPlanCommand,
    fact_id_map: dict[str, str],
    swot_report_registry: SWOTReportRegistry,
    prompts_config: UpdateExistingSectionPromptConfig,
) -> SWOTReportComponentSection:
    ## Validate the command
    if command.target_section_id is None:
        raise InvalidPlanException(
            f"Target section ID is required for {command.command} command"
        )

    ## Retrieve the existing section
    existing_section = swot_report_registry.retrieve_section(
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
    system_prompt = Template(prompts_config.system_prompt).render(
        component=component,
        company_name=company_name,
    )

    ## Prepare the user message
    user_message = Template(prompts_config.user_prompt).render(
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
        llm_service=llm_service,
        llm=llm,
        output_model=SWOTReportComponentSection,
    )
    ## Validate the result
    if updated_section is None:
        raise FailedToUpdateExistingSectionException(
            f"Failed to update existing section for component {component}"
        )

    _LOGGER.info(f"Updated section for component {component}")

    return updated_section
