from typing import Any

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit.tools.config import get_configuration_dict

from unique_toolkit._common.default_language_model import DEFAULT_GPT_35_TURBO
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.evals.context_relevancy.schema import StructuredOutputConfig


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
        DEFAULT_GPT_35_TURBO,
        description="The language model to use for the chunk relevancy sort.",
    )
    fallback_language_model: LMI = get_LMI_default_field(
        DEFAULT_GPT_35_TURBO,
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
    max_tasks: int | SkipJsonSchema[None] = Field(
        default=1000,
        description="The maximum number of tasks to run in parallel.",
    )
