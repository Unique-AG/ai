from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.generation.agentic.prompts.commands.create_new_section.config import (
    CreateNewSectionPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.commands.update_existing_section.config import (
    UpdateExistingSectionPromptConfig,
)


class CommandsPromptConfig(BaseModel):
    model_config = get_configuration_dict()

    create_new_section_prompt_config: CreateNewSectionPromptConfig = Field(
        default=CreateNewSectionPromptConfig(),
        description="The prompt config for the create new section command.",
    )
    update_existing_section_prompt_config: UpdateExistingSectionPromptConfig = Field(
        default=UpdateExistingSectionPromptConfig(),
        description="The prompt config for the update existing section command.",
    )
