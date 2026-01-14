"""Configuration for generation handler."""

from pydantic import BaseModel, Field

from unique_toolkit._common.experimental.write_up_agent.services.generation_handler.prompts.config import (
    GenerationHandlerPromptsConfig,
)
from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.language_model.default_language_model import DEFAULT_GPT_4o


class GenerationHandlerConfig(BaseModel):
    """Configuration for generation handler.

    This configuration controls how groups are batched, how prompts are built,
    and how the LLM is called for generating summaries.
    """

    model_config = get_configuration_dict()

    language_model: LMI = get_LMI_default_field(
        DEFAULT_GPT_4o,
        description="The language model to use for generating summaries.",
    )

    common_instruction: str = Field(
        default="You are a technical writer. Summarize the provided content concisely and clearly.",
        description="Common instruction applied to all groups",
    )

    # TODO [UN-16142]: Add default instructions for each group
    group_specific_instructions: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Custom instructions per group. "
            "Keys should be formatted as 'column:value' (e.g., 'section:Introduction')"
        ),
    )

    max_tokens_per_batch: int = Field(
        default=4000,
        ge=100,
        description="Maximum tokens per batch for LLM input (affects batching strategy)",
    )

    max_rows_per_batch: int = Field(
        default=20,
        ge=1,
        description="Maximum rows per batch (secondary limit to tokens)",
    )

    prompts_config: GenerationHandlerPromptsConfig = Field(
        default_factory=GenerationHandlerPromptsConfig,
        description="Configuration for the prompts.",
    )
