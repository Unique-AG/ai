from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.source_management.iteration.prompts.config import (
    SourceIterationPromptConfig,
)


class SourceIterationConfig(BaseModel):
    model_config = get_configuration_dict()

    max_number_of_selected_chunks: int = Field(
        default=5,
        description="The maximum number of chunks to select to make the decision of selecting the source.",
    )
    prompt_config: SourceIterationPromptConfig = Field(
        default_factory=SourceIterationPromptConfig,
        description="The configuration for the source iteration prompts.",
    )
