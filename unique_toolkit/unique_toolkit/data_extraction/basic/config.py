from pydantic import BaseModel

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.data_extraction.basic.prompt import (
    DEFAULT_DATA_EXTRACTION_SYSTEM_PROMPT,
    DEFAULT_DATA_EXTRACTION_USER_PROMPT,
)
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o


class StructuredOutputDataExtractorConfig(BaseModel):
    model_config = get_configuration_dict()

    language_model: LMI = get_LMI_default_field(DEFAULT_GPT_4o)
    structured_output_enforce_schema: bool = False
    system_prompt_template: str = DEFAULT_DATA_EXTRACTION_SYSTEM_PROMPT
    user_prompt_template: str = DEFAULT_DATA_EXTRACTION_USER_PROMPT
