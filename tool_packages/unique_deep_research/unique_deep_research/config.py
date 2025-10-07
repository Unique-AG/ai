from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.infos import LanguageModelName

# Global template environment for the deep research tool
TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


class DeepResearchEngine(StrEnum):
    """Available deep research engines."""

    OPENAI = "OpenAI"
    UNIQUE_CUSTOM = "UniqueCustom"


# Hardcoded configuration for the unique custom engine
@dataclass
class UniqueCustomEngineConfig:
    max_parallel_researchers: int = 3
    max_research_iterations: int = 5
    max_tool_calls_per_researcher: int = 10


RESPONSES_API_TIMEOUT_SECONDS = 3600


class BaseEngine(BaseModel):
    type: DeepResearchEngine = Field(
        default=DeepResearchEngine.UNIQUE_CUSTOM, json_schema_extra={"exclude": True}
    )
    small_model: LMI | LanguageModelName = Field(
        description="A smaller fast model for less demanding tasks",
        default=LanguageModelName.AZURE_GPT_4o_2024_1120,
    )
    large_model: LMI | LanguageModelName = Field(
        description="A larger model with longer context window and more powerful capabilities",
        default=LanguageModelName.AZURE_GPT_41_2025_0414,
    )
    research_model: LMI | LanguageModelName = Field(
        description="The main research model to be used for conducting research",
        default=LanguageModelName.AZURE_GPT_41_2025_0414,
    )

    def get_type(self) -> DeepResearchEngine:
        return self.type


class OpenAIEngine(BaseEngine):
    type: DeepResearchEngine = Field(
        default=DeepResearchEngine.OPENAI, json_schema_extra={"exclude": True}
    )
    research_model: LMI | LanguageModelName = Field(
        description="The main research model to be used for conducting research. This must be an OpenAI model hosted directly on OpenAI's servers. eg. litellm:openai-gpt-5",
        default=LanguageModelName.LITELLM_OPENAI_GPT_5,
    )


class UniqueEngine(BaseEngine):
    pass


class DeepResearchToolConfig(BaseToolConfig):
    engine: UniqueEngine | OpenAIEngine = Field(
        description="The deep research engine to use. Please be aware that OpenAI engine requires particular models to be used as the research model and they have different tools available.",
        default_factory=UniqueEngine,
    )
