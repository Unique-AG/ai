from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model.infos import LanguageModelName

from unique_swot.services.summarization.prompts.config import SummarizationPromptConfig


class SummarizationConfig(BaseModel):
    model_config = get_configuration_dict()

    language_model: LMI = get_LMI_default_field(
        LanguageModelName.AZURE_GPT_4o_2024_1120,
        description="The language model to use for the summarization.",
    )

    prompt_config: SummarizationPromptConfig = Field(
        default_factory=SummarizationPromptConfig,
        description="The configuration for the summarization prompts.",
    )
