from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.source_management.selection.prompts.config import (
    SourceSelectionPromptConfig,
)


class SourceSelectionConfig(BaseModel):
    model_config = get_configuration_dict()

    max_number_of_selected_chunks: int = Field(
        default=50,
        description="The maximum number of chunks to select to make the decision of selecting the source.",
    )
    prompt_config: SourceSelectionPromptConfig = Field(
        default_factory=SourceSelectionPromptConfig,
        description="The configuration for the source selection prompts.",
    )
