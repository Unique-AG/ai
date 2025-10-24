from logging import getLogger

from pydantic import BaseModel, Field
from unique_toolkit._common.default_language_model import (
    DEFAULT_GPT_4o,
)
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.config import get_configuration_dict

_LOGGER = getLogger(__name__)

_DEFAULT_LANGUAGE_MODEL = DEFAULT_GPT_4o
_DEFAULT_BATCH_SIZE = 3
_DEFAULT_MAX_TOKENS_PER_BATCH = 30_000


class ReportGenerationConfig(BaseModel):
    """
    Configuration settings for SWOT report generation.

    Controls the language model, batching behavior, and token limits for report generation.

    Attributes:
        language_model: The language model to use for generation
        batch_size: Number of sources to process in each batch
        max_tokens_per_batch: Maximum tokens allowed per batch to prevent overflow
    """

    model_config = get_configuration_dict()

    language_model: LMI = get_LMI_default_field(
        _DEFAULT_LANGUAGE_MODEL, description="The language model to use for generation"
    )
    batch_size: int = Field(
        default=_DEFAULT_BATCH_SIZE,
        description="Number of sources to process in each batch",
    )
    max_tokens_per_batch: int = Field(
        default=_DEFAULT_MAX_TOKENS_PER_BATCH,
        description="Maximum tokens allowed per batch to prevent overflow",
    )
