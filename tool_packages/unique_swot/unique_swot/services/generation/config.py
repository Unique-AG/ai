from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic.rjsf_tags import RJSFMetaTag
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.infos import (
    LanguageModelName,
)

from unique_swot.services.generation.agentic.config import AgenticGeneratorConfig

_DEFAULT_LANGUAGE_MODEL = LanguageModelName.AZURE_GPT_5_2025_0807


class GenerationMode(StrEnum):
    """Controls the orchestration strategy for report generation."""

    INTERLEAVED = "interleaved"
    """Extract, plan, and generate per source (current default)."""

    EXTRACT_FIRST = "extract_first"
    """Extract facts from all sources first, then plan and generate once per component."""

    @classmethod
    def get_ui_enum_names(cls) -> list[str]:
        # Return the names of enums
        # Important: The order of the names must be the same as the order of the enums
        return [
            "Interleaved (extract + plan per source)",
            "Extract First (extract all, then plan once)",
        ]


class ReportGenerationConfig(BaseModel):
    """
    Configuration settings for SWOT report generation.

    Controls the language model, batching behavior, and token limits for report generation.

    Attributes:
        language_model: The language model to use for generation
        generation_mode: The orchestration strategy to use
    """

    model_config = get_configuration_dict()

    generation_mode: Annotated[
        GenerationMode,
        RJSFMetaTag(
            {
                "ui:widget": "radio",
                "ui:title": "Generation Strategy",
                "ui:enumNames": GenerationMode.get_ui_enum_names(),
            }
        ),
    ] = Field(
        default=GenerationMode.INTERLEAVED,
        description="Controls how sources are processed during report generation.",
        title="Generation Strategy",
    )
    language_model: LMI = get_LMI_default_field(
        _DEFAULT_LANGUAGE_MODEL, description="The language model to use for generation"
    )
    agentic_generator_config: AgenticGeneratorConfig = Field(
        default_factory=AgenticGeneratorConfig,
        description="The configuration for the agentic generator.",
    )
