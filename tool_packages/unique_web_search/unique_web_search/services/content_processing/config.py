from enum import StrEnum

from pydantic import BaseModel, Field
from unique_toolkit import LanguageModelName
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.tools.config import get_configuration_dict


class ContentProcessingStartegy(StrEnum):
    SUMMARIZE = "summarize"
    TRUNCATE = "truncate"
    NONE = "none"


class WebPageChunk(BaseModel):
    url: str
    display_link: str
    title: str
    snippet: str
    content: str
    order: str


class ContentProcessingConfig(BaseModel):
    model_config = get_configuration_dict()

    # Processing strategy - simple enum instead of complex discriminated union
    strategy: ContentProcessingStartegy = Field(
        default=ContentProcessingStartegy.NONE,
        description="The content processing strategy to use",
    )

    # Language model configuration
    language_model: LanguageModelInfo = Field(
        default=LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120),
        description="The language model to use for processing",
    )

    # Cleaning configuration
    clean_enabled: bool = Field(
        default=False,
        description="Whether to enable LLM-based content cleaning before processing",
    )
    cleaning_prompt: str = Field(
        default="""You are a content cleaning specialist. Your job is to:

1. Remove navigation elements, advertisements, and UI clutter
2. Keep all substantive content, headings, and structure
3. Convert to clean markdown format
4. Preserve important links and references
5. Remove duplicate or redundant sections

Focus on clarity and readability while preserving all meaningful information.""",
        description="The system prompt for LLM-based content cleaning",
    )

    # Processing configuration - simplified with hardcoded smart defaults
    max_tokens: int = Field(
        default=5000,
        description="Max tokens for truncation and summarization",
    )
    summarization_prompt: str = Field(
        default="""You are a helping assistant that generates query focused summarization of a webpage content. The summary should convey any information that is relevant to the query.""",
        description="The system prompt to use for summarization",
    )


ContentAdapterConfig = ContentProcessingConfig
