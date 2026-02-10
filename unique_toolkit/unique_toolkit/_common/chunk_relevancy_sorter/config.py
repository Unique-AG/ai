from typing import Annotated, Any

from pydantic import BaseModel, Field

from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.evaluation.context_relevancy.schema import (
    StructuredOutputConfig,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.default_language_model import DEFAULT_LANGUAGE_MODEL


class ChunkRelevancySortConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=False,
        description="Whether to enable the chunk relevancy sort.",
    )
    relevancy_levels_to_consider: list[str] = Field(
        default=["high", "medium", "low"],
        description="The relevancy levels to consider.",
    )
    relevancy_level_order: dict[str, int] = Field(
        default={"high": 0, "medium": 1, "low": 2},
        description="The relevancy level order.",
    )
    language_model: LMI = get_LMI_default_field(
        DEFAULT_LANGUAGE_MODEL,
        description="The language model to use for the chunk relevancy sort.",
    )
    fallback_language_model: LMI = get_LMI_default_field(
        DEFAULT_LANGUAGE_MODEL,
        description="The language model to use as a fallback.",
    )
    additional_llm_options: dict[str, Any] = Field(
        default={},
        description="Additional options to pass to the language model.",
    )
    structured_output_config: StructuredOutputConfig = Field(
        default_factory=StructuredOutputConfig,
        description="The configuration for the structured output.",
    )
    max_tasks: (
        Annotated[int, Field(title="Limited")]
        | Annotated[None, Field(title="Unlimited")]
    ) = Field(
        default=1000,
        description="The maximum number of tasks to run in parallel.",
    )
