from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.generation.prompts.summarization.components import (
    OPPORTUNITIES_SUMMARIZATION_SYSTEM_PROMPT,
    STRENGTHS_SUMMARIZATION_SYSTEM_PROMPT,
    THREATS_SUMMARIZATION_SYSTEM_PROMPT,
    WEAKNESSES_SUMMARIZATION_SYSTEM_PROMPT,
)


class SummarizationPromptConfig(BaseModel):
    model_config = get_configuration_dict()

    opportunities: str = Field(
        default=OPPORTUNITIES_SUMMARIZATION_SYSTEM_PROMPT,
        description="The prompt for the opportunities extraction.",
    )
    weaknesses: str = Field(
        default=WEAKNESSES_SUMMARIZATION_SYSTEM_PROMPT,
        description="The prompt for the weaknesses extraction.",
    )
    strengths: str = Field(
        default=STRENGTHS_SUMMARIZATION_SYSTEM_PROMPT,
        description="The prompt for the strengths extraction.",
    )
    threats: str = Field(
        default=THREATS_SUMMARIZATION_SYSTEM_PROMPT,
        description="The prompt for the threats extraction.",
    )
