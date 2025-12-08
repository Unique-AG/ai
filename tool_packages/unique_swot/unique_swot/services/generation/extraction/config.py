from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

from unique_swot.services.generation.extraction.prompts.config import (
    ExtractionPromptConfig,
)

_DEFAULT_BATCH_SIZE = 30
_DEFAULT_MAX_TOKENS_PER_BATCH = 30_000


class ExtractionConfig(BaseModel):
    model_config = get_configuration_dict()

    prompt_config: ExtractionPromptConfig = Field(
        default_factory=ExtractionPromptConfig,
        description="The configuration for the extraction prompt.",
    )

    batch_size: int = Field(
        default=_DEFAULT_BATCH_SIZE,
        description="Number of sources to process in each batch",
    )
    max_tokens_per_batch: int = Field(
        default=_DEFAULT_MAX_TOKENS_PER_BATCH,
        description="Maximum tokens allowed per batch to prevent overflow",
    )
