from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from pydantic import Field
from unique_toolkit._common.validators import LMI
from unique_toolkit.agentic.tools.schemas import BaseToolConfig
from unique_toolkit.language_model.infos import LanguageModelInfo, LanguageModelName

# Global template environment for the deep research tool
TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


class DeepResearchEngine(StrEnum):
    """Available deep research engines."""

    OPENAI = "OpenAI"
    UNIQUE_CUSTOM = "UniqueCustom"


@dataclass
class UniqueCustomEngineConfig:
    max_parallel_researchers: int = 3
    max_research_iterations: int = 5
    max_tool_calls_per_researcher: int = 10


class DeepResearchToolConfig(BaseToolConfig):
    small_model: LMI = Field(
        description="The model to use for less demanding tasks",
        default=LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120),
    )
    large_model: LMI = Field(
        description="The model to use for more demanding tasks",
        default=LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_41_2025_0414),
    )
    research_model: LMI = Field(
        description="The main research model to be used",
        default=LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_41_2025_0414),
    )
    engine: DeepResearchEngine = Field(
        description="The deep research engine to use",
        default=DeepResearchEngine.OPENAI,
    )


RESPONSES_API_TIMEOUT_SECONDS = 3600
