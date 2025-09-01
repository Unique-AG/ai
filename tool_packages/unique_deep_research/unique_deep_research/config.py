from enum import StrEnum

from pydantic import BaseModel, Field
from unique_toolkit.evals.schemas import EvaluationMetricName
from unique_toolkit.tools.schemas import BaseToolConfig


class DeepResearchEngine(StrEnum):
    """Available deep research engines."""

    OPENAI = "openai"


class OpenAIEngineConfig(BaseModel):
    """Configuration specific to OpenAI deep research engine."""

    research_model: str = Field(
        description="The model to use for the deep research tool. Required to responses api compatible.",
        default="litellm:o4-mini-deep-research-2025-06-26",
    )


class DeepResearchToolConfig(BaseToolConfig):
    engine: DeepResearchEngine = Field(
        description="The deep research engine to use",
        default=DeepResearchEngine.OPENAI,
    )
    openai_config: OpenAIEngineConfig = Field(
        description="Configuration for OpenAI engine",
        default_factory=OpenAIEngineConfig,
    )
    clarifying_model: str = Field(
        description="The model to use for the clarifying agent.",
        default="AZURE_GPT_41_2025_0414",
    )
    research_brief_model: str = Field(
        description="The model to use for the research brief agent.",
        default="litellm:anthropic/claude-sonnet-4-20250514",
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
