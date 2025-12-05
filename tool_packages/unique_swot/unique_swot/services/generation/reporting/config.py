from pydantic import BaseModel, Field
from unique_toolkit import LanguageModelName
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI, get_LMI_default_field

from unique_swot.services.generation.reporting.prompts.config import (
    ReportingPromptConfig,
)

_DEFAULT_LANGUAGE_MODEL = LanguageModelName.AZURE_GPT_5_2025_0807


class ReportingConfig(BaseModel):
    """
    Configuration settings for SWOT reporting.
    """

    model_config = get_configuration_dict()

    language_model: LMI = get_LMI_default_field(
        _DEFAULT_LANGUAGE_MODEL, description="The language model to use for reporting"
    )
    reporting_prompt_config: ReportingPromptConfig = Field(
        default_factory=ReportingPromptConfig,
        description="The configuration for the reporting prompts.",
    )
