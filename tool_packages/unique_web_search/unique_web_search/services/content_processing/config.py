from enum import StrEnum

from pydantic import BaseModel, Field
from unidecode import unidecode
from unique_toolkit import LanguageModelName
from unique_toolkit.content.schemas import ContentChunk
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

    def to_content_chunk(self) -> "ContentChunk":
        """Convert WebPageChunk to ContentChunk format."""

        # Convert to ascii
        title = unidecode(self.title)
        name = f'{self.display_link}: "{title}"'

        return ContentChunk(
            id=name,
            text=self.content,
            order=int(self.order),
            start_page=None,
            end_page=None,
            key=name,
            chunk_id=self.order,
            url=self.url,
            title=name,
        )


REGEX_PATTERNS = [
    r"^[\*\+\-]\s+(Home|Menu|Navigate|Skip to|Sign In|Subscribe).*$",
    r"^[\?\[]?(Subscribe|Sign [Iu]p|Follow|Share|Like)[\]?]?.*$",
    r"Cookie.*|Privacy Policy|Terms of Service",
    r"^\s*\[.*accessibility.*\].*$",
    r"https?://[^\s\])]+",
]


class ContentProcessorConfig(BaseModel):
    model_config = get_configuration_dict()

    strategy: ContentProcessingStartegy = Field(
        default=ContentProcessingStartegy.NONE,
        description="The content processing strategy to use",
    )
    regex_preprocessing_patterns: list[str] = Field(
        default=REGEX_PATTERNS,
        description="Regex patterns for preprocessing to remove navigation, UI clutter, ads, and links. Default includes the aformentioned common patterns for cleanup. Leave empty if you want to skip this preprocessing step.",
    )
    language_model: LanguageModelInfo = Field(
        default=LanguageModelInfo.from_name(LanguageModelName.AZURE_GPT_4o_2024_1120),
        description="The language model to use for SUMMARIZE strategy",
    )
    max_tokens: int = Field(
        default=5000,
        description="Max tokens for truncation and summarization",
    )
    summarization_prompt: str = Field(
        default="""You are a helping assistant that generates query focused summarization of a webpage content. The summary should convey any information that is relevant to the query.""",
        description="The system prompt to use for summarization",
    )
