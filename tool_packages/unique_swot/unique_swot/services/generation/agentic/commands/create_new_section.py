import json
from logging import getLogger

from unique_toolkit import LanguageModelService
from unique_toolkit._common.validators import LMI

from unique_swot.services.generation.agentic.exceptions import (
    FailedToCreateNewSectionException,
)
from unique_swot.services.generation.agentic.models.base import (
    SWOTReportComponentSection,
)
from unique_swot.services.generation.agentic.models.plan import GenerationPlanCommand
from unique_swot.services.generation.agentic.prompts.commands import (
    CREATE_NEW_SECTION_SYSTEM_PROMPT,
    CREATE_NEW_SECTION_USER_PROMPT,
)
from unique_swot.services.generation.context import SWOTComponent
from unique_swot.utils import generate_structured_output

_LOGGER = getLogger(__name__)


async def create_new_section(
    *,
    llm: LMI,
    llm_service: LanguageModelService,
    component: SWOTComponent,
    instruction: str,
    command: GenerationPlanCommand,
    fact_id_map: dict[str, str],
    company_name: str,
    output_model: type[SWOTReportComponentSection] = SWOTReportComponentSection,
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
        company_name=company_name,
    )
    user_message = CREATE_NEW_SECTION_USER_PROMPT.render(
        facts=facts,
        instruction=instruction,
        model_name=output_model.__name__,
        model_schema=json.dumps(output_model.model_json_schema(), indent=1),
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

    _LOGGER.debug(
        f"Created section for component {component}:\n {created_section.model_dump_json(indent=1)}"
    )

    return created_section
