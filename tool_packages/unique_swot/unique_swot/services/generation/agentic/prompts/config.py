from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.generation.agentic.prompts.commands.config import (
    CommandsPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.definition.config import (
    ComponentDefinitionPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.extraction.config import (
    ExtractionPromptConfig,
)
from unique_swot.services.generation.agentic.prompts.plan.config import PlanPromptConfig


class AgenticPromptsConfig(BaseModel):
    model_config = get_configuration_dict()

    commands_prompt_config: CommandsPromptConfig = Field(
        default=CommandsPromptConfig(),
        description="The prompt config for the commands.",
    )

    extraction_prompt_config: ExtractionPromptConfig = Field(
        default=ExtractionPromptConfig(),
        description="The prompt config for the extraction.",
    )

    plan_prompt_config: PlanPromptConfig = Field(
        default=PlanPromptConfig(),
        description="The prompt config for the plan.",
    )

    definition_prompt_config: ComponentDefinitionPromptConfig = Field(
        default=ComponentDefinitionPromptConfig(),
        description="The prompt config for the definition.",
    )
