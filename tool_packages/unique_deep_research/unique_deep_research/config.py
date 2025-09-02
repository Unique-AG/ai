from enum import StrEnum

from pydantic import BaseModel, Field
from unique_toolkit._common.validators import LMI
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.tools.schemas import BaseToolConfig


class DeepResearchEngine(StrEnum):
    """Available deep research engines."""

    OPENAI = "OpenAI"


class OpenAIEngineConfig(BaseModel):
    """Configuration specific to OpenAI deep research engine."""

    research_model: LMI = Field(
        description="The model to use for the deep research tool. Required to be responses API compatible.",
        default=LanguageModelInfo.from_name(
            LanguageModelName.LITELLM_OPENAI_O4_MINI_DEEP_RESEARCH
        ),
    )


class EngineConfig(BaseModel):
    """Configuration for a deep research engine."""

    OpenAI: OpenAIEngineConfig = Field(
        description="Configuration for OpenAI engine",
        default_factory=OpenAIEngineConfig,
    )


class DeepResearchToolConfig(BaseToolConfig):
    engine: DeepResearchEngine = Field(
        description="The deep research engine to use",
        default=DeepResearchEngine.OPENAI,
    )
    engine_config: EngineConfig = Field(
        description="Configuration for the deep research engine",
        default_factory=EngineConfig,
    )
    clarifying_model: LMI = Field(
        description="The model to use for the clarifying agent.",
        default=LanguageModelInfo.from_name(LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4),
    )
    research_brief_model: LMI = Field(
        description="The model to use for the research brief agent.",
        default=LanguageModelInfo.from_name(LanguageModelName.ANTHROPIC_CLAUDE_OPUS_4),
    )
    tool_call_description: str = Field(
        description="The description to use for the tool call in the language model",
        default="Use this tool for complex research tasks that require deep investigation",
    )
    evaluation_check_list: list[EvaluationMetricName] = Field(
        default=[EvaluationMetricName.HALLUCINATION],
        description="The list of evaluation metrics to check.",
    )
    tool_description_for_system_prompt: str = Field(
        description="System prompt description for the deep research tool",
        default=(
            "The DeepResearch tool is for complex research tasks that require:\n"
            "- In-depth investigation across multiple sources\n"
            "- Synthesis of information from various perspectives\n"
            "- Comprehensive analysis with citations\n"
            "- Detailed reports on specific topics\n\n"
        ),
    )


RESPONSES_API_TIMEOUT_SECONDS = 3600
