from pydantic import BaseModel, Field
from unique_toolkit._common.pydantic_helpers import get_configuration_dict

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


class LineRemovalPatternsConfig(BaseModel):
    model_config = get_configuration_dict()
    enabled: bool = Field(
        default=True,
        title="Enable Line Removal",
        description="When enabled, automatically removes irrelevant lines from web pages such as navigation links, cookie notices, and sign-in buttons.",
    )
    patterns: list[str] = Field(
        default=REGEX_LINE_REMOVAL_PATTERNS,
        title="Removal Patterns",
        description="List of text patterns used to identify and remove irrelevant lines. Each pattern is a regular expression. Leave empty to skip line removal.",
    )


# Pattern/replacement pairs for content transformation
LINK_AND_URL_CLEANUP_PATTERNS = [
    # Transform markdown links: [text](url) → [text]
    (r"\[([^\]]+)\]\([^)]+\)", r"[\1]"),
    # Remove standalone URLs
    (r"https?://[^\s\])]+ ?", r""),
    # Normalize whitespace
    (r"\n{3,}", r"\n\n"),
    (r"[ \t]{2,}", r" "),
]


class CleaningConfig(BaseModel):
    model_config = get_configuration_dict()

    line_removal: LineRemovalPatternsConfig = Field(
        default_factory=LineRemovalPatternsConfig,
        title="Line Removal",
        description="Remove irrelevant lines from web pages, such as navigation menus, cookie banners, and sign-in buttons.",
    )

    enable_markdown_cleaning: bool = Field(
        default=True,
        title="Enable Link and URL Cleanup",
        description="When enabled, simplifies or removes web links and URLs from the content to improve readability.",
    )
