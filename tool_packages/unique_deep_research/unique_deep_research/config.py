from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from unique_toolkit._common.validators import LMI, get_LMI_default_field
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.infos import LanguageModelName

# Global template environment for the deep research tool
TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


class DeepResearchEngine(StrEnum):
    """Available deep research engines."""

    OPENAI = "OpenAI"
    UNIQUE = "Unique"


# Hardcoded configuration for the unique custom engine
@dataclass
class UniqueCustomEngineConfig:
    max_parallel_researchers: int = 5
    max_research_iterations_lead_researcher: int = 6
    max_research_iterations_sub_researcher: int = 10


RESPONSES_API_TIMEOUT_SECONDS = 3600


class BaseEngine(BaseModel):
    engine_type: Literal[DeepResearchEngine.UNIQUE, DeepResearchEngine.OPENAI] = Field(
        description="The type of engine to use for deep research"
    )
    small_model: LMI = get_LMI_default_field(
        LanguageModelName.AZURE_GPT_4o_2024_1120,
        description="A smaller fast model for less demanding tasks",
    )

    large_model: LMI = get_LMI_default_field(
        LanguageModelName.AZURE_GPT_41_2025_0414,
        description="A larger model with longer context window and more powerful capabilities",
    )

    research_model: LMI = get_LMI_default_field(
        LanguageModelName.AZURE_GPT_41_2025_0414,
        description="The main research model to be used for conducting research",
    )

    def get_type(self) -> DeepResearchEngine:
        return DeepResearchEngine(self.engine_type)


class OpenAIEngine(BaseEngine):
    engine_type: Literal[DeepResearchEngine.OPENAI] = Field(
        default=DeepResearchEngine.OPENAI
    )
    research_model: LMI = get_LMI_default_field(
        LanguageModelName.LITELLM_OPENAI_GPT_5,
        description="The main research model to be used for conducting research. This must be an OpenAI model hosted directly on OpenAI's servers. eg. litellm:openai-gpt-5",
    )


class UniqueEngine(BaseEngine):
    engine_type: Literal[DeepResearchEngine.UNIQUE] = Field(
        default=DeepResearchEngine.UNIQUE
    )


class DeepResearchToolConfig(BaseToolConfig):
    engine: UniqueEngine | OpenAIEngine = Field(
        description="The deep research engine to use. Please be aware that OpenAI engine requires particular models to be used as the research model and they have different tools available.",
        default=UniqueEngine(),
        discriminator="engine_type",
    )
