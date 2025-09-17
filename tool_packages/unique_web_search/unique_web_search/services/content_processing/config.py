from enum import StrEnum

from pydantic import BaseModel, Field
from unidecode import unidecode
from unique_toolkit import LanguageModelName
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.language_model.infos import LanguageModelInfo
from unique_toolkit.agentic.tools.config import get_configuration_dict


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


# Patterns that remove entire lines
REGEX_LINE_REMOVAL_PATTERNS = [
    # Skip navigation elements only (not content navigation)
    r"^[\*\+\-]?\s*(Skip to|Skip Navigation|Jump to|Accessibility help).*$",
    # Standalone authentication links (not part of content)
    r"^\s*(Sign In|Log In|Register|Sign Up|Create Account|My Account)\s*$",
    # Social media and newsletter signup buttons
    r"^[\?\[]?\s*(Subscribe|Follow Us|Share This|Newsletter Sign Up)\s*[\]?]?$",
    # Legal/Privacy footer elements (specific phrases)
    r"^.*(Cookie Policy|Privacy Policy|Terms of Service|Cookie Settings|Accept Cookies|Cookie Notice).*$",
    # Accessibility labels
    r"^\s*\[.*accessibility.*\].*$",
]

# Pattern/replacement pairs for content transformation
REGEX_CONTENT_TRANSFORMATIONS = [
    # Transform markdown links: [text](url) → [text]
    (r"\[([^\]]+)\]\([^)]+\)", r"[\1]"),
    # Remove standalone URLs
    (r"https?://[^\s\])]+ ?", ""),
]


class ContentProcessorConfig(BaseModel):
    model_config = get_configuration_dict()

    strategy: ContentProcessingStartegy = Field(
        default=ContentProcessingStartegy.NONE,
        description="The content processing strategy to use",
    )
    regex_line_removal_patterns: list[str] = Field(
        default=REGEX_LINE_REMOVAL_PATTERNS,
        description="Regex patterns for removing entire lines that match (navigation, UI clutter, etc.). Leave empty to skip line removal.",
    )
    remove_urls_from_markdown_links: bool = Field(
        default=True,
        description="Whether to remove URLs from markdown links in website content.",
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
